"""LLM tabanlı log analiz modülü."""

import json
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from .log_reader import LogEntry


@dataclass
class Alert:
    """Bir alarmı temsil eder."""
    severity: str  # critical, error, warning, info
    summary: str
    details: str
    log_line: str
    recommendation: str
    source_name: str = ""
    source_type: str = ""

    @property
    def severity_level(self) -> int:
        """Severity'yi sayısal değere çevir."""
        levels = {"info": 0, "warning": 1, "error": 2, "critical": 3}
        return levels.get(self.severity.lower(), 0)


class LLMAnalyzer:
    """OpenAI API kullanarak log analizi yapan sınıf."""

    SEVERITY_LEVELS = {"info": 0, "warning": 1, "error": 2, "critical": 3}

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 500,
        prompt_template: str = "",
        severity_threshold: str = "warning"
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.prompt_template = prompt_template
        self.severity_threshold = severity_threshold

    def _build_prompt(self, entries: list[LogEntry]) -> str:
        """Log entry'lerinden prompt oluştur."""
        logs_text = "\n".join([
            f"[{e.source_name}:{e.line_number}] {e.line}"
            for e in entries
        ])
        return self.prompt_template.format(logs=logs_text)

    def _extract_json(self, text: str) -> str | None:
        """Metinden JSON bloğunu çıkar."""
        # ```json ... ``` bloğunu ara
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json_match.group(1).strip()

        # ``` ... ``` bloğunu ara
        code_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if code_match:
            content = code_match.group(1).strip()
            if content.startswith('{'):
                return content

        # Direkt JSON bul
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return text[start:end]

        return None

    def _parse_response(self, response_text: str, entries: list[LogEntry]) -> list[Alert]:
        """LLM yanıtını parse et."""
        alerts = []

        print(f"[DEBUG] LLM Response:\n{response_text[:500]}...")

        try:
            json_str = self._extract_json(response_text)

            if not json_str:
                print("[HATA] JSON bloğu bulunamadı")
                return alerts

            data = json.loads(json_str)

            if not data.get("has_issues", False):
                print("[INFO] has_issues=false, alarm yok")
                return alerts

            # Entry'lerin source bilgisini bir dict'e koy
            source_map = {e.line: (e.source_name, e.source_type) for e in entries}

            for alert_data in data.get("alerts", []):
                log_line = alert_data.get("log_line", "")
                source_name, source_type = source_map.get(log_line, ("unknown", "unknown"))

                # Eğer source bulunamadıysa demo olarak ata
                if source_name == "unknown":
                    source_name = "demo"
                    source_type = "application"

                alert = Alert(
                    severity=alert_data.get("severity", "info"),
                    summary=alert_data.get("summary", ""),
                    details=alert_data.get("details", ""),
                    log_line=log_line,
                    recommendation=alert_data.get("recommendation", ""),
                    source_name=source_name,
                    source_type=source_type
                )
                alerts.append(alert)

            print(f"[INFO] {len(alerts)} alarm parse edildi")

        except json.JSONDecodeError as e:
            print(f"[HATA] JSON parse hatası: {e}")
            print(f"[DEBUG] JSON string: {json_str[:300] if json_str else 'None'}...")
        except Exception as e:
            print(f"[HATA] Response parse hatası: {e}")

        return alerts

    def _filter_by_severity(self, alerts: list[Alert]) -> list[Alert]:
        """Severity threshold'a göre filtrele."""
        threshold_level = self.SEVERITY_LEVELS.get(self.severity_threshold.lower(), 1)
        return [a for a in alerts if a.severity_level >= threshold_level]

    def analyze(self, entries: list[LogEntry]) -> list[Alert]:
        """Log entry'lerini analiz et ve alert'leri döndür."""
        if not entries:
            return []

        prompt = self._build_prompt(entries)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Sen bir sistem güvenlik ve log analiz uzmanısın. Yanıtlarını her zaman belirtilen JSON formatında ver."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.1  # Daha tutarlı sonuçlar için düşük temperature
            )

            response_text = response.choices[0].message.content or ""
            alerts = self._parse_response(response_text, entries)
            return self._filter_by_severity(alerts)

        except Exception as e:
            print(f"[HATA] OpenAI API hatası: {e}")
            return []

    def analyze_batch(self, entries: list[LogEntry], batch_size: int = 50) -> list[Alert]:
        """Büyük log listelerini batch'ler halinde analiz et."""
        all_alerts = []

        for i in range(0, len(entries), batch_size):
            batch = entries[i:i + batch_size]
            alerts = self.analyze(batch)
            all_alerts.extend(alerts)

        return all_alerts
