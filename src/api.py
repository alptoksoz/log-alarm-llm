"""FastAPI Web API."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import Config
from .llm_analyzer import Alert, LLMAnalyzer
from .log_reader import LogReader

app = FastAPI(title="Log Alarm LLM", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
config: Optional[Config] = None
log_reader: Optional[LogReader] = None
analyzer: Optional[LLMAnalyzer] = None
alert_history: list[dict] = []


class AnalyzeRequest(BaseModel):
    source_name: Optional[str] = None
    line_count: int = 100


class LogLine(BaseModel):
    source: str
    line: str
    line_number: int


@app.on_event("startup")
async def startup():
    """Uygulama başlangıcında config yükle."""
    global config, log_reader, analyzer

    config = Config()
    log_reader = LogReader(config.log_sources)
    analyzer = LLMAnalyzer(
        api_key=config.openai_api_key,
        model=config.openai_model,
        max_tokens=config.openai_max_tokens,
        prompt_template=config.prompt_template,
        severity_threshold=config.severity_threshold
    )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Ana sayfa - Dashboard HTML."""
    html_path = Path(__file__).parent.parent / "static" / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>Log Alarm LLM</h1><p>static/index.html bulunamadı</p>"


@app.get("/api/sources")
async def get_sources():
    """Aktif log kaynaklarını listele."""
    return {
        "sources": [
            {
                "name": s["name"],
                "path": s["path"],
                "type": s["type"],
                "exists": Path(s["path"]).exists()
            }
            for s in config.log_sources
        ]
    }


@app.get("/api/logs/{source_name}")
async def get_logs(source_name: str, lines: int = 50):
    """Belirli bir kaynaktan son logları getir."""
    source = next((s for s in config.log_sources if s["name"] == source_name), None)

    if not source:
        raise HTTPException(status_code=404, detail=f"Kaynak bulunamadı: {source_name}")

    if not Path(source["path"]).exists():
        raise HTTPException(status_code=404, detail=f"Log dosyası bulunamadı: {source['path']}")

    entries = log_reader.read_last_n_lines(source, n=lines)

    return {
        "source": source_name,
        "count": len(entries),
        "lines": [
            {"line": e.line, "line_number": e.line_number}
            for e in entries
        ]
    }


@app.post("/api/analyze")
async def analyze_logs(request: AnalyzeRequest):
    """Logları analiz et ve alarmları döndür."""
    global alert_history

    entries = []

    if request.source_name:
        # Tek kaynak
        source = next((s for s in config.log_sources if s["name"] == request.source_name), None)
        if not source:
            raise HTTPException(status_code=404, detail=f"Kaynak bulunamadı: {request.source_name}")
        entries = log_reader.read_last_n_lines(source, n=request.line_count)
    else:
        # Tüm kaynaklar
        for source in config.log_sources:
            entries.extend(log_reader.read_last_n_lines(source, n=request.line_count))

    if not entries:
        return {"alerts": [], "message": "Analiz edilecek log bulunamadı"}

    # Analiz
    alerts = analyzer.analyze_batch(entries, config.batch_size)

    # Geçmişe ekle
    timestamp = datetime.now().isoformat()
    for alert in alerts:
        alert_history.append({
            "timestamp": timestamp,
            "severity": alert.severity,
            "summary": alert.summary,
            "details": alert.details,
            "log_line": alert.log_line,
            "recommendation": alert.recommendation,
            "source_name": alert.source_name,
            "source_type": alert.source_type
        })

    # Son 100 alarm tut
    alert_history = alert_history[-100:]

    return {
        "analyzed_lines": len(entries),
        "alert_count": len(alerts),
        "alerts": [
            {
                "severity": a.severity,
                "summary": a.summary,
                "details": a.details,
                "log_line": a.log_line,
                "recommendation": a.recommendation,
                "source_name": a.source_name
            }
            for a in alerts
        ]
    }


@app.get("/api/alerts/history")
async def get_alert_history(limit: int = 50):
    """Alarm geçmişini getir."""
    return {
        "count": len(alert_history),
        "alerts": alert_history[-limit:][::-1]  # En yeni önce
    }


@app.delete("/api/alerts/history")
async def clear_alert_history():
    """Alarm geçmişini temizle."""
    global alert_history
    alert_history = []
    return {"message": "Geçmiş temizlendi"}


@app.get("/api/status")
async def get_status():
    """Sistem durumunu getir."""
    return {
        "status": "running",
        "model": config.openai_model,
        "severity_threshold": config.severity_threshold,
        "sources_count": len(config.log_sources),
        "alert_history_count": len(alert_history)
    }


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Sunucuyu başlat."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
