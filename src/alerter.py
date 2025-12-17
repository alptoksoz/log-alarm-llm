"""Alarm gönderim modülü (Console + Email)."""

import smtplib
from abc import ABC, abstractmethod
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .llm_analyzer import Alert


class BaseAlerter(ABC):
    """Temel alerter sınıfı."""

    @abstractmethod
    def send(self, alerts: list[Alert]) -> bool:
        """Alarmları gönder."""
        pass


class ConsoleAlerter(BaseAlerter):
    """Terminal'e alarm yazdıran sınıf."""

    COLORS = {
        "critical": "\033[91m",  # Kırmızı
        "error": "\033[91m",     # Kırmızı
        "warning": "\033[93m",   # Sarı
        "info": "\033[94m",      # Mavi
        "reset": "\033[0m",
        "bold": "\033[1m",
    }

    def __init__(self, colored: bool = True):
        self.colored = colored

    def _colorize(self, text: str, color: str) -> str:
        """Metni renklendir."""
        if not self.colored:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def send(self, alerts: list[Alert]) -> bool:
        """Alarmları terminale yazdır."""
        if not alerts:
            return True

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(self._colorize(f"  LOG ALARMLARI - {timestamp}", "bold"))
        print(f"{'='*60}\n")

        for i, alert in enumerate(alerts, 1):
            severity_colored = self._colorize(
                f"[{alert.severity.upper()}]",
                alert.severity.lower()
            )

            print(f"{severity_colored} {self._colorize(alert.summary, 'bold')}")
            print(f"   Kaynak: {alert.source_name} ({alert.source_type})")
            print(f"   Detay: {alert.details}")
            print(f"   Log: {alert.log_line[:100]}..." if len(alert.log_line) > 100 else f"   Log: {alert.log_line}")
            print(f"   Öneri: {alert.recommendation}")
            print()

        print(f"{'='*60}")
        print(f"  Toplam {len(alerts)} alarm")
        print(f"{'='*60}\n")

        return True


class EmailAlerter(BaseAlerter):
    """Email ile alarm gönderen sınıf."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str]
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def _build_html_body(self, alerts: list[Alert]) -> str:
        """HTML email body oluştur."""
        severity_colors = {
            "critical": "#dc3545",
            "error": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8"
        }

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert {{ border-left: 4px solid; padding: 10px; margin: 10px 0; background: #f8f9fa; }}
                .critical {{ border-color: #dc3545; }}
                .error {{ border-color: #dc3545; }}
                .warning {{ border-color: #ffc107; }}
                .info {{ border-color: #17a2b8; }}
                .severity {{ font-weight: bold; padding: 2px 8px; border-radius: 3px; color: white; }}
                .log-line {{ font-family: monospace; background: #e9ecef; padding: 5px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h2>Log Alarm Raporu</h2>
            <p><strong>Zaman:</strong> {timestamp}</p>
            <p><strong>Toplam Alarm:</strong> {len(alerts)}</p>
            <hr>
        """

        for alert in alerts:
            color = severity_colors.get(alert.severity.lower(), "#6c757d")
            html += f"""
            <div class="alert {alert.severity.lower()}">
                <span class="severity" style="background: {color};">{alert.severity.upper()}</span>
                <strong>{alert.summary}</strong>
                <p><strong>Kaynak:</strong> {alert.source_name} ({alert.source_type})</p>
                <p><strong>Detay:</strong> {alert.details}</p>
                <div class="log-line">{alert.log_line}</div>
                <p><strong>Öneri:</strong> {alert.recommendation}</p>
            </div>
            """

        html += """
        </body>
        </html>
        """
        return html

    def send(self, alerts: list[Alert]) -> bool:
        """Alarmları email ile gönder."""
        if not alerts:
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[LOG ALARM] {len(alerts)} yeni alarm tespit edildi"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)

            # Plain text versiyon
            text_body = "Log Alarm Raporu\n\n"
            for alert in alerts:
                text_body += f"[{alert.severity.upper()}] {alert.summary}\n"
                text_body += f"Detay: {alert.details}\n"
                text_body += f"Öneri: {alert.recommendation}\n\n"

            # HTML versiyon
            html_body = self._build_html_body(alerts)

            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())

            print(f"[INFO] Email gönderildi: {len(alerts)} alarm")
            return True

        except Exception as e:
            print(f"[HATA] Email gönderimi başarısız: {e}")
            return False


class AlertManager:
    """Birden fazla alerter'ı yöneten sınıf."""

    def __init__(self):
        self.alerters: list[BaseAlerter] = []

    def add_alerter(self, alerter: BaseAlerter) -> None:
        """Alerter ekle."""
        self.alerters.append(alerter)

    def send_all(self, alerts: list[Alert]) -> dict[str, bool]:
        """Tüm alerter'lara gönder."""
        results = {}
        for alerter in self.alerters:
            name = alerter.__class__.__name__
            results[name] = alerter.send(alerts)
        return results
