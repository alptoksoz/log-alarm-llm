# Log Alarm LLM

**AI Destekli Log Analiz ve Alarm Sistemi**

Log dosyalarını OpenAI GPT modelleri ile analiz eden, güvenlik tehditleri ve sistem anomalilerini tespit edip alarm üreten Python uygulaması.

---

## İçindekiler

1. [Proje Özeti](#proje-özeti)
2. [Mimari](#mimari)
3. [Kurulum](#kurulum)
4. [Konfigürasyon](#konfigürasyon)
5. [Kullanım](#kullanım)
6. [Kod Açıklamaları](#kod-açıklamaları)
7. [API Referansı](#api-referansı)
8. [Demo Log Dosyaları](#demo-log-dosyaları)
9. [Geliştirme](#geliştirme)

---

## Proje Özeti

### Amaç

Geleneksel log analiz sistemleri pattern matching (regex) kullanır ve sadece önceden tanımlanmış tehditleri tespit edebilir. Bu proje, **LLM (Large Language Model)** kullanarak:

- **Bağlamsal analiz** yapar - log satırlarını bir arada değerlendirir
- **Yeni tehdit türlerini** tanıyabilir - eğitim seti dışındaki anomalileri fark eder
- **İnsan-okunabilir raporlar** üretir - teknik olmayan kişiler için açıklamalar sağlar
- **Öneriler sunar** - her tehdit için aksiyon planı önerir

### Özellikler

| Özellik | Açıklama |
|---------|----------|
| Multi-Source | Birden fazla log kaynağını aynı anda izler |
| Real-time | Daemon modu ile sürekli izleme |
| Web Dashboard | Modern React-benzeri tek sayfa arayüz |
| Email Alerts | SMTP üzerinden email bildirimleri |
| Batch Processing | Büyük log dosyalarını parçalara böler |
| Log Rotation | Dönen log dosyalarını otomatik handle eder |

### Teknoloji Stack

```
Python 3.10+
├── openai        - GPT API entegrasyonu
├── FastAPI       - REST API ve web sunucu
├── uvicorn       - ASGI sunucu
├── PyYAML        - Konfigürasyon yönetimi
└── smtplib       - Email gönderimi (built-in)
```

---

## Mimari

### Sistem Diyagramı

```
┌─────────────────────────────────────────────────────────────────┐
│                         LOG KAYNAKLARI                          │
├─────────────┬─────────────┬─────────────┬─────────────┬────────┤
│  nginx.log  │  auth.log   │  syslog     │  app.log    │  ...   │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴────────┘
       │             │             │             │
       └─────────────┴──────┬──────┴─────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │      LogReader        │
                │  (log_reader.py)      │
                │  - Dosya izleme       │
                │  - Position tracking  │
                │  - Log rotation       │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │     LLMAnalyzer       │
                │  (llm_analyzer.py)    │
                │  - OpenAI API call    │
                │  - JSON parsing       │
                │  - Severity filter    │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │     AlertManager      │
                │    (alerter.py)       │
                │  - ConsoleAlerter     │
                │  - EmailAlerter       │
                └───────────┬───────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   ┌──────────┐      ┌──────────┐      ┌──────────┐
   │ Terminal │      │  Email   │      │  Web UI  │
   │ (stdout) │      │  (SMTP)  │      │ (FastAPI)│
   └──────────┘      └──────────┘      └──────────┘
```

### Veri Akışı

```
1. Log Dosyası → LogReader → LogEntry[]
2. LogEntry[] → LLMAnalyzer → Prompt + OpenAI API
3. API Response → JSON Parse → Alert[]
4. Alert[] → AlertManager → Console/Email/Web
```

---

## Kurulum

### Gereksinimler

- Python 3.10 veya üstü
- OpenAI API anahtarı
- (Opsiyonel) SMTP hesabı email bildirimleri için

### Adımlar

```bash
# 1. Proje dizinine git
cd log-alarm-llm

# 2. Virtual environment oluştur
python3 -m venv venv

# 3. Aktifleştir
source venv/bin/activate  # Linux/Mac
# veya
.\venv\Scripts\activate   # Windows

# 4. Bağımlılıkları yükle
pip install -r requirements.txt

# 5. API anahtarını ayarla
export OPENAI_API_KEY="sk-your-api-key-here"

# 6. Çalıştır
python -m src.main --web
```

### requirements.txt

```
openai>=1.0.0      # OpenAI Python SDK v1.x
pyyaml>=6.0        # YAML parser
fastapi>=0.104.0   # Web framework
uvicorn>=0.24.0    # ASGI server
```

---

## Konfigürasyon

Tüm ayarlar `config/config.yaml` dosyasında tanımlanır.

### Örnek Konfigürasyon

```yaml
# OpenAI API ayarları
openai:
  api_key: "${OPENAI_API_KEY}"  # Env variable'dan alınır
  model: "gpt-4o-mini"          # Maliyet-etkin model
  max_tokens: 2000              # Yanıt uzunluğu limiti

# İzlenecek log dosyaları
log_sources:
  - name: "nginx"               # Kaynak adı (UI'da görünür)
    path: "./logs/nginx.log"    # Dosya yolu
    type: "webserver"           # Kategori
    enabled: true               # Aktif/pasif

  - name: "auth"
    path: "./logs/auth.log"
    type: "system"
    enabled: true

# Analiz ayarları
analysis:
  batch_size: 50                # Kaç satır birden analiz edilsin
  interval_seconds: 60          # Daemon modunda kontrol aralığı
  severity_threshold: "info"    # Minimum alarm seviyesi

# Alarm ayarları
alerting:
  console:
    enabled: true
    colored: true               # ANSI renk kodları

  email:
    enabled: false
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    username: "your-email@gmail.com"
    password: "${EMAIL_PASSWORD}"
    from_addr: "your-email@gmail.com"
    to_addrs:
      - "admin@example.com"

# LLM Prompt şablonu
prompt_template: |
  Sen bir güvenlik ve sistem analisti gibi davran...
  {logs}
```

### Environment Variables

| Değişken | Açıklama |
|----------|----------|
| `OPENAI_API_KEY` | OpenAI API anahtarı (zorunlu) |
| `EMAIL_PASSWORD` | SMTP şifresi (email aktifse) |

---

## Kullanım

### CLI Modları

```bash
# 1. Tek seferlik analiz (CI/CD için ideal)
python -m src.main --once

# 2. Sürekli izleme (production için)
python -m src.main --daemon

# 3. Web arayüzü (demo/test için)
python -m src.main --web
python -m src.main --web --port 3000  # Farklı port

# 4. Özel config dosyası
python -m src.main --config /path/to/config.yaml --daemon
```

### Web Arayüzü

`http://localhost:8000` adresinde açılır:

- **Log Kaynakları**: Sol panelden kaynak seçimi
- **Log Görüntüleyici**: Seçilen kaynağın son logları
- **Analiz Et**: LLM'e gönderip sonuç al
- **Alarm Geçmişi**: Tüm tespit edilen alarmlar

---

## Kod Açıklamaları

### Dizin Yapısı

```
log-alarm-llm/
├── config/
│   └── config.yaml       # Merkezi konfigürasyon
├── logs/                  # Demo log dosyaları
│   ├── nginx_access.log
│   ├── auth.log
│   ├── syslog
│   ├── database.log
│   ├── app_clean.log
│   └── demo.log
├── src/
│   ├── __init__.py
│   ├── config.py         # Konfigürasyon yükleyici
│   ├── log_reader.py     # Log dosyası okuyucu
│   ├── llm_analyzer.py   # OpenAI entegrasyonu
│   ├── alerter.py        # Alarm gönderici
│   ├── api.py            # FastAPI web sunucu
│   └── main.py           # CLI entry point
├── static/
│   └── index.html        # Web dashboard UI
├── requirements.txt
└── README.md
```

---

### 1. config.py - Konfigürasyon Yönetimi

**Dosya**: `src/config.py` (88 satır)

Bu modül YAML konfigürasyon dosyasını yükler ve environment variable'ları çözümler.

#### Temel Fonksiyonlar

```python
def resolve_env_vars(value: Any) -> Any:
    """
    String içindeki ${VAR} formatındaki değişkenleri çözümler.

    Örnek:
        "${OPENAI_API_KEY}" → "sk-abc123..."

    Recursive olarak dict ve list içindeki değerleri de işler.
    """
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.environ.get(var_name, "")
            value = value.replace(f"${{{var_name}}}", env_value)
        return value
    elif isinstance(value, dict):
        return {k: resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_env_vars(item) for item in value]
    return value
```

#### Config Sınıfı

```python
class Config:
    """
    Konfigürasyona tip-güvenli erişim sağlar.

    Properties:
        openai_api_key: str     - API anahtarı
        openai_model: str       - Model adı (gpt-4o-mini)
        log_sources: list[dict] - Aktif log kaynakları
        batch_size: int         - Batch boyutu
        prompt_template: str    - LLM prompt şablonu
    """

    def __init__(self, config_path: str | None = None):
        self._config = load_config(config_path)

    @property
    def log_sources(self) -> list[dict]:
        # Sadece enabled=true olanları döndür
        return [s for s in self._config["log_sources"] if s.get("enabled", True)]
```

#### Kullanım

```python
config = Config()
print(config.openai_model)      # "gpt-4o-mini"
print(config.log_sources)       # [{"name": "nginx", ...}, ...]
```

---

### 2. log_reader.py - Log Dosyası Okuyucu

**Dosya**: `src/log_reader.py` (130 satır)

Log dosyalarını okuyan ve izleyen modül.

#### LogEntry Dataclass

```python
@dataclass
class LogEntry:
    """Tek bir log satırını temsil eder."""
    source_name: str    # Kaynak adı (nginx, auth, vb.)
    source_type: str    # Kategori (webserver, system, vb.)
    line: str           # Log satırı içeriği
    line_number: int    # Satır numarası
```

#### LogReader Sınıfı

```python
class LogReader:
    """
    Log dosyalarını okuyan ve izleyen sınıf.

    Özellikler:
    - Position tracking: Son okunan yeri hatırlar
    - Log rotation: Dosya küçülürse baştan okur
    - Error handling: Permission/read hatalarını yakalar
    """

    def __init__(self, log_sources: list[dict]):
        self.log_sources = log_sources
        self._file_positions: dict[str, int] = {}  # path → byte position
```

#### Temel Metodlar

```python
def read_new_lines(self, source: dict) -> Generator[LogEntry, None, None]:
    """
    Son okumadan bu yana eklenen yeni satırları okur.

    Algoritma:
    1. Dosya boyutunu kontrol et
    2. Eğer boyut < son_pozisyon → log rotation olmuş, baştan başla
    3. Son pozisyondan itibaren oku
    4. Yeni pozisyonu kaydet
    """
    path = source["path"]
    file_size = os.path.getsize(path)
    last_position = self._get_file_position(path)

    # Log rotation kontrolü
    if file_size < last_position:
        last_position = 0

    with open(path, "r") as f:
        f.seek(last_position)
        for line in f:
            yield LogEntry(...)
        self._set_file_position(path, f.tell())

def read_last_n_lines(self, source: dict, n: int = 100) -> list[LogEntry]:
    """
    Dosyanın son n satırını okur.
    Web UI'da kullanılır.
    """

def initialize_positions(self) -> None:
    """
    Tüm dosyaların pozisyonlarını sona ayarlar.
    Daemon modunda sadece yeni logları izlemek için.
    """
```

#### Batch Helper

```python
def batch_entries(entries: list[LogEntry], batch_size: int) -> Generator[list[LogEntry], None, None]:
    """Log entry'lerini batch'lere böl."""
    for i in range(0, len(entries), batch_size):
        yield entries[i:i + batch_size]
```

---

### 3. llm_analyzer.py - LLM Entegrasyonu

**Dosya**: `src/llm_analyzer.py` (179 satır)

OpenAI API ile log analizi yapan ana modül.

#### Alert Dataclass

```python
@dataclass
class Alert:
    """Bir alarmı temsil eder."""
    severity: str       # critical, error, warning, info
    summary: str        # Kısa açıklama
    details: str        # Detaylı bilgi
    log_line: str       # İlgili log satırı
    recommendation: str # Önerilen aksiyon
    source_name: str    # Kaynak adı
    source_type: str    # Kaynak tipi

    @property
    def severity_level(self) -> int:
        """Severity'yi sayısal değere çevir (filtreleme için)."""
        levels = {"info": 0, "warning": 1, "error": 2, "critical": 3}
        return levels.get(self.severity.lower(), 0)
```

#### LLMAnalyzer Sınıfı

```python
class LLMAnalyzer:
    """
    OpenAI API kullanarak log analizi yapan sınıf.

    Parametreler:
        api_key: OpenAI API anahtarı
        model: Kullanılacak model (default: gpt-4o-mini)
        max_tokens: Maksimum yanıt token sayısı
        prompt_template: LLM'e gönderilecek prompt şablonu
        severity_threshold: Minimum alarm seviyesi
    """

    SEVERITY_LEVELS = {"info": 0, "warning": 1, "error": 2, "critical": 3}

    def __init__(self, api_key, model, max_tokens, prompt_template, severity_threshold):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        # ...
```

#### Prompt Oluşturma

```python
def _build_prompt(self, entries: list[LogEntry]) -> str:
    """
    Log entry'lerinden prompt oluştur.

    Format:
        [kaynak:satır_no] log satırı
        [nginx:45] 192.168.1.1 - GET /api/users...
    """
    logs_text = "\n".join([
        f"[{e.source_name}:{e.line_number}] {e.line}"
        for e in entries
    ])
    return self.prompt_template.format(logs=logs_text)
```

#### JSON Extraction

LLM yanıtları bazen markdown code block içinde gelir. Bu fonksiyon JSON'u çıkarır:

```python
def _extract_json(self, text: str) -> str | None:
    """
    Metinden JSON bloğunu çıkar.

    Desteklenen formatlar:
    1. ```json ... ```
    2. ``` ... ```
    3. Düz { ... }
    """
    # 1. ```json ... ``` bloğunu ara
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        return json_match.group(1).strip()

    # 2. ``` ... ``` bloğunu ara
    code_match = re.search(r'```\s*([\s\S]*?)\s*```', text)
    if code_match:
        content = code_match.group(1).strip()
        if content.startswith('{'):
            return content

    # 3. Direkt JSON bul
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]

    return None
```

#### OpenAI API Çağrısı

```python
def analyze(self, entries: list[LogEntry]) -> list[Alert]:
    """Log entry'lerini analiz et ve alert'leri döndür."""

    prompt = self._build_prompt(entries)

    response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {
                "role": "system",
                "content": "Sen bir sistem güvenlik ve log analiz uzmanısın. "
                          "Yanıtlarını her zaman belirtilen JSON formatında ver."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=self.max_tokens,
        temperature=0.1  # Düşük temperature = tutarlı sonuçlar
    )

    response_text = response.choices[0].message.content
    alerts = self._parse_response(response_text, entries)
    return self._filter_by_severity(alerts)
```

#### Batch Processing

```python
def analyze_batch(self, entries: list[LogEntry], batch_size: int = 50) -> list[Alert]:
    """Büyük log listelerini batch'ler halinde analiz et."""
    all_alerts = []
    for i in range(0, len(entries), batch_size):
        batch = entries[i:i + batch_size]
        alerts = self.analyze(batch)
        all_alerts.extend(alerts)
    return all_alerts
```

---

### 4. alerter.py - Alarm Gönderici

**Dosya**: `src/alerter.py` (196 satır)

Alarmları çeşitli kanallara gönderen modül.

#### BaseAlerter (Abstract)

```python
class BaseAlerter(ABC):
    """Temel alerter interface'i."""

    @abstractmethod
    def send(self, alerts: list[Alert]) -> bool:
        """Alarmları gönder. Başarı durumunu döndür."""
        pass
```

#### ConsoleAlerter

```python
class ConsoleAlerter(BaseAlerter):
    """
    Terminal'e renkli alarm yazdıran sınıf.

    Renk kodları (ANSI):
        critical/error: Kırmızı (\033[91m)
        warning: Sarı (\033[93m)
        info: Mavi (\033[94m)
    """

    COLORS = {
        "critical": "\033[91m",  # Kırmızı
        "error": "\033[91m",     # Kırmızı
        "warning": "\033[93m",   # Sarı
        "info": "\033[94m",      # Mavi
        "reset": "\033[0m",
        "bold": "\033[1m",
    }

    def send(self, alerts: list[Alert]) -> bool:
        """Alarmları terminale yazdır."""
        for alert in alerts:
            severity_colored = self._colorize(
                f"[{alert.severity.upper()}]",
                alert.severity.lower()
            )
            print(f"{severity_colored} {alert.summary}")
            print(f"   Kaynak: {alert.source_name}")
            print(f"   Detay: {alert.details}")
            print(f"   Öneri: {alert.recommendation}")
        return True
```

#### EmailAlerter

```python
class EmailAlerter(BaseAlerter):
    """
    SMTP üzerinden HTML email gönderen sınıf.

    Özellikler:
    - Plain text + HTML multipart
    - Severity'ye göre renkli kartlar
    - TLS şifreleme
    """

    def __init__(self, smtp_host, smtp_port, username, password, from_addr, to_addrs):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        # ...

    def _build_html_body(self, alerts: list[Alert]) -> str:
        """HTML email body oluştur."""
        # Bootstrap-benzeri kartlar ile styled email
        html = """
        <html>
        <head>
            <style>
                .alert { border-left: 4px solid; padding: 10px; }
                .critical { border-color: #dc3545; }
                .warning { border-color: #ffc107; }
            </style>
        </head>
        <body>
            <h2>Log Alarm Raporu</h2>
            ...
        </body>
        </html>
        """
        return html

    def send(self, alerts: list[Alert]) -> bool:
        """Alarmları email ile gönder."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[LOG ALARM] {len(alerts)} yeni alarm"

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
```

#### AlertManager

```python
class AlertManager:
    """
    Birden fazla alerter'ı yöneten sınıf.

    Kullanım:
        manager = AlertManager()
        manager.add_alerter(ConsoleAlerter())
        manager.add_alerter(EmailAlerter(...))
        manager.send_all(alerts)
    """

    def __init__(self):
        self.alerters: list[BaseAlerter] = []

    def add_alerter(self, alerter: BaseAlerter) -> None:
        self.alerters.append(alerter)

    def send_all(self, alerts: list[Alert]) -> dict[str, bool]:
        """Tüm alerter'lara gönder, sonuçları döndür."""
        results = {}
        for alerter in self.alerters:
            name = alerter.__class__.__name__
            results[name] = alerter.send(alerts)
        return results
```

---

### 5. api.py - FastAPI Web Sunucu

**Dosya**: `src/api.py` (206 satır)

REST API ve web arayüzü sağlayan modül.

#### FastAPI App

```python
app = FastAPI(title="Log Alarm LLM", version="0.1.0")

# CORS - tüm origin'lere izin ver (development için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Global State

```python
# Uygulama seviyesinde paylaşılan objeler
config: Optional[Config] = None
log_reader: Optional[LogReader] = None
analyzer: Optional[LLMAnalyzer] = None
alert_history: list[dict] = []  # Son 100 alarm

@app.on_event("startup")
async def startup():
    """Uygulama başlangıcında config yükle."""
    global config, log_reader, analyzer
    config = Config()
    log_reader = LogReader(config.log_sources)
    analyzer = LLMAnalyzer(...)
```

#### Endpoint'ler

```python
@app.get("/", response_class=HTMLResponse)
async def root():
    """Ana sayfa - Dashboard HTML."""
    html_path = Path(__file__).parent.parent / "static" / "index.html"
    return html_path.read_text()

@app.get("/api/sources")
async def get_sources():
    """Aktif log kaynaklarını listele."""
    return {
        "sources": [
            {"name": s["name"], "path": s["path"], "type": s["type"]}
            for s in config.log_sources
        ]
    }

@app.get("/api/logs/{source_name}")
async def get_logs(source_name: str, lines: int = 50):
    """Belirli bir kaynaktan son logları getir."""
    entries = log_reader.read_last_n_lines(source, n=lines)
    return {"source": source_name, "lines": [...]}

@app.post("/api/analyze")
async def analyze_logs(request: AnalyzeRequest):
    """Logları analiz et ve alarmları döndür."""
    alerts = analyzer.analyze_batch(entries, config.batch_size)

    # Geçmişe ekle (son 100 alarm)
    for alert in alerts:
        alert_history.append({...})
    alert_history = alert_history[-100:]

    return {"alert_count": len(alerts), "alerts": [...]}

@app.get("/api/alerts/history")
async def get_alert_history(limit: int = 50):
    """Alarm geçmişini getir."""
    return {"alerts": alert_history[-limit:][::-1]}

@app.get("/api/status")
async def get_status():
    """Sistem durumunu getir."""
    return {
        "status": "running",
        "model": config.openai_model,
        "sources_count": len(config.log_sources)
    }
```

---

### 6. main.py - CLI Entry Point

**Dosya**: `src/main.py` (216 satır)

Komut satırı arayüzü ve ana uygulama.

#### LogAlarmApp Sınıfı

```python
class LogAlarmApp:
    """
    Ana uygulama sınıfı.

    Modlar:
    - run_once(): Tek seferlik analiz
    - run_daemon(): Sürekli izleme
    """

    def __init__(self, config_path: str | None = None):
        self.config = Config(config_path)
        self.running = False

        self.log_reader = LogReader(self.config.log_sources)
        self.analyzer = LLMAnalyzer(...)
        self.alert_manager = AlertManager()
        self._setup_alerters()

    def _setup_alerters(self) -> None:
        """Config'e göre alerter'ları ayarla."""
        if self.config.console_alerting.get("enabled"):
            self.alert_manager.add_alerter(ConsoleAlerter())

        if self.config.email_alerting.get("enabled"):
            self.alert_manager.add_alerter(EmailAlerter(...))
```

#### Daemon Modu

```python
def run_daemon(self) -> None:
    """Sürekli izleme modunda çalış."""
    self.running = True

    # Signal handler'ları ayarla (graceful shutdown)
    signal.signal(signal.SIGINT, self._handle_signal)
    signal.signal(signal.SIGTERM, self._handle_signal)

    # Sadece yeni logları izle
    self.log_reader.initialize_positions()

    print(f"[INFO] Log izleme başlatıldı (interval: {self.config.interval_seconds}s)")

    while self.running:
        entries = self.log_reader.read_all_new_lines()

        if entries:
            print(f"[INFO] {len(entries)} yeni log satırı tespit edildi")
            alerts = self.analyzer.analyze_batch(entries)

            if alerts:
                self.alert_manager.send_all(alerts)

        time.sleep(self.config.interval_seconds)

def _handle_signal(self, signum, frame) -> None:
    """SIGINT/SIGTERM handler."""
    print("\n[INFO] Durdurma sinyali alındı, çıkılıyor...")
    self.running = False
```

#### CLI Argümanları

```python
def main():
    parser = argparse.ArgumentParser(
        description="Log Alarm LLM - Log analizi ve alarm sistemi"
    )

    parser.add_argument("--config", "-c", help="Config dosyası yolu")
    parser.add_argument("--once", action="store_true", help="Tek seferlik analiz")
    parser.add_argument("--daemon", "-d", action="store_true", help="Sürekli izleme")
    parser.add_argument("--web", "-w", action="store_true", help="Web arayüzü")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Port")

    args = parser.parse_args()

    if args.web:
        import uvicorn
        from .api import app
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    elif args.once:
        app = LogAlarmApp(args.config)
        app.run_once()
    elif args.daemon:
        app = LogAlarmApp(args.config)
        app.run_daemon()
```

---

## API Referansı

### GET /api/sources

Aktif log kaynaklarını listeler.

**Response:**
```json
{
  "sources": [
    {
      "name": "nginx",
      "path": "./logs/nginx_access.log",
      "type": "webserver",
      "exists": true
    }
  ]
}
```

### GET /api/logs/{source_name}

Belirli kaynaktan son logları getirir.

**Parameters:**
- `source_name` (path): Kaynak adı
- `lines` (query, default=50): Kaç satır

**Response:**
```json
{
  "source": "nginx",
  "count": 50,
  "lines": [
    {"line": "192.168.1.1 - GET /api...", "line_number": 1}
  ]
}
```

### POST /api/analyze

Logları LLM ile analiz eder.

**Request Body:**
```json
{
  "source_name": "nginx",
  "line_count": 100
}
```

**Response:**
```json
{
  "analyzed_lines": 100,
  "alert_count": 3,
  "alerts": [
    {
      "severity": "critical",
      "summary": "SQL Injection saldırısı tespit edildi",
      "details": "...",
      "log_line": "...",
      "recommendation": "WAF kurallarını güçlendirin",
      "source_name": "nginx"
    }
  ]
}
```

### GET /api/alerts/history

Alarm geçmişini getirir.

**Parameters:**
- `limit` (query, default=50): Kaç alarm

**Response:**
```json
{
  "count": 25,
  "alerts": [
    {
      "timestamp": "2025-12-16T10:30:00",
      "severity": "warning",
      "summary": "..."
    }
  ]
}
```

### GET /api/status

Sistem durumunu getirir.

**Response:**
```json
{
  "status": "running",
  "model": "gpt-4o-mini",
  "severity_threshold": "info",
  "sources_count": 6,
  "alert_history_count": 25
}
```

---

## Demo Log Dosyaları

### 1. nginx_access.log (Web Sunucu)

**İçerik**: HTTP istekleri
**Tehditler**:
- SQL Injection (`UNION SELECT`, `OR 1=1`)
- XSS saldırıları (`<script>alert()`)
- Directory traversal (`../../../etc/passwd`)
- Admin panel tarama

### 2. auth.log (Kimlik Doğrulama)

**İçerik**: SSH ve sudo logları
**Tehditler**:
- Brute force saldırısı (aynı IP'den tekrarlanan başarısız girişler)
- Şüpheli saatlerde root erişimi
- Bilinmeyen konumdan oturum açma

### 3. syslog (Sistem)

**İçerik**: Kernel ve sistem mesajları
**Tehditler**:
- OOM (Out of Memory) kill
- CPU throttling (aşırı sıcaklık)
- Disk arızası (SMART uyarıları)
- SYN flood saldırısı
- Disk doluluk uyarıları

### 4. database.log (Veritabanı)

**İçerik**: MySQL/PostgreSQL logları
**Tehditler**:
- Yavaş sorgular (45+ saniye)
- Connection limit aşımı
- Deadlock
- Timeout hataları

### 5. app_clean.log (Temiz Uygulama)

**İçerik**: Normal uygulama aktivitesi
**Tehditler**: YOK - alarm üretmemeli

### 6. demo.log (Karışık)

**İçerik**: Tüm tehdit türlerinin karışımı
**Amaç**: Demo ve test için

---

## Geliştirme

### Yeni Alerter Ekleme

```python
# src/my_alerter.py
from src.alerter import BaseAlerter, Alert
import requests

class SlackAlerter(BaseAlerter):
    """Slack'e alarm gönderen sınıf."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, alerts: list[Alert]) -> bool:
        payload = {
            "text": f":warning: {len(alerts)} yeni alarm tespit edildi!",
            "attachments": [
                {
                    "color": self._get_color(a.severity),
                    "title": a.summary,
                    "text": a.details
                }
                for a in alerts
            ]
        }
        response = requests.post(self.webhook_url, json=payload)
        return response.ok

    def _get_color(self, severity: str) -> str:
        return {"critical": "danger", "warning": "warning"}.get(severity, "good")
```

### Yeni Log Kaynağı Ekleme

`config/config.yaml`:
```yaml
log_sources:
  - name: "custom_app"
    path: "/var/log/custom/app.log"
    type: "application"
    enabled: true
```

### Prompt Özelleştirme

`config/config.yaml`:
```yaml
prompt_template: |
  Sen bir güvenlik uzmanısın. Aşağıdaki logları analiz et.

  Özellikle şunlara dikkat et:
  - SQL injection
  - Brute force
  - Unauthorized access

  Çıktı formatı (JSON):
  {{
    "alerts": [...],
    "has_issues": true/false
  }}

  Log satırları:
  {logs}
```

### Test Etme

```bash
# Virtual env aktifken
source venv/bin/activate

# API key set
export OPENAI_API_KEY="sk-..."

# Tek seferlik test
python -m src.main --once

# Web UI test
python -m src.main --web --port 8000
# Tarayıcıda http://localhost:8000 aç
```

---

## Sorun Giderme

### "JSON parse hatası" Alıyorum

LLM yanıtı beklenmeyen formatta. Çözümler:
1. `max_tokens` değerini artır (2000+)
2. Debug loglarına bak (`[DEBUG] LLM Response:`)
3. `temperature` değerini düşür (0.1)

### Email Gönderilmiyor

Gmail için:
1. 2FA aktif olmalı
2. App Password oluştur: https://myaccount.google.com/apppasswords
3. Normal şifre yerine App Password kullan

### Log Dosyası Bulunamıyor

1. `config.yaml`'daki path'i kontrol et
2. Relative path kullanıyorsan proje root'undan itibaren yaz
3. Dosya izinlerini kontrol et (`chmod +r`)

---

## Lisans

MIT License

---

## Katkıda Bulunma

1. Fork et
2. Feature branch oluştur (`git checkout -b feature/amazing`)
3. Commit et (`git commit -m 'Add amazing feature'`)
4. Push et (`git push origin feature/amazing`)
5. Pull Request aç
