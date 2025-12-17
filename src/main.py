#!/usr/bin/env python3
"""Log Alarm LLM - Ana uygulama."""

import argparse
import signal
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from .alerter import AlertManager, ConsoleAlerter, EmailAlerter
from .config import Config
from .llm_analyzer import LLMAnalyzer
from .log_reader import LogReader


class LogAlarmApp:
    """Ana uygulama sınıfı."""

    def __init__(self, config_path: str | None = None):
        self.config = Config(config_path)
        self.running = False

        # Log reader
        self.log_reader = LogReader(self.config.log_sources)

        # LLM Analyzer
        self.analyzer = LLMAnalyzer(
            api_key=self.config.openai_api_key,
            model=self.config.openai_model,
            max_tokens=self.config.openai_max_tokens,
            prompt_template=self.config.prompt_template,
            severity_threshold=self.config.severity_threshold
        )

        # Alert Manager
        self.alert_manager = AlertManager()
        self._setup_alerters()

    def _setup_alerters(self) -> None:
        """Alerter'ları ayarla."""
        # Console alerter
        console_config = self.config.console_alerting
        if console_config.get("enabled", True):
            self.alert_manager.add_alerter(
                ConsoleAlerter(colored=console_config.get("colored", True))
            )

        # Email alerter
        email_config = self.config.email_alerting
        if email_config.get("enabled", False):
            self.alert_manager.add_alerter(
                EmailAlerter(
                    smtp_host=email_config["smtp_host"],
                    smtp_port=email_config["smtp_port"],
                    username=email_config["username"],
                    password=email_config["password"],
                    from_addr=email_config["from_addr"],
                    to_addrs=email_config["to_addrs"]
                )
            )

    def _handle_signal(self, signum, frame) -> None:
        """SIGINT/SIGTERM handler."""
        print("\n[INFO] Durdurma sinyali alındı, çıkılıyor...")
        self.running = False

    def run_once(self) -> int:
        """Tek seferlik analiz yap ve alarm sayısını döndür."""
        print("[INFO] Loglar okunuyor...")

        entries = []
        for source in self.config.log_sources:
            source_entries = self.log_reader.read_last_n_lines(source, n=100)
            entries.extend(source_entries)
            print(f"  - {source['name']}: {len(source_entries)} satır")

        if not entries:
            print("[INFO] Analiz edilecek log bulunamadı")
            return 0

        print(f"[INFO] Toplam {len(entries)} satır analiz ediliyor...")

        alerts = self.analyzer.analyze_batch(entries, self.config.batch_size)

        if alerts:
            self.alert_manager.send_all(alerts)
            return len(alerts)
        else:
            print("[INFO] Alarm üretecek bir durum tespit edilmedi")
            return 0

    def run_daemon(self) -> None:
        """Sürekli izleme modunda çalış."""
        self.running = True

        # Signal handler'ları ayarla
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Pozisyonları başlat (sadece yeni logları izle)
        self.log_reader.initialize_positions()

        print(f"[INFO] Log izleme başlatıldı (interval: {self.config.interval_seconds}s)")
        print(f"[INFO] İzlenen kaynaklar: {[s['name'] for s in self.config.log_sources]}")
        print("[INFO] Durdurmak için Ctrl+C")

        while self.running:
            try:
                entries = self.log_reader.read_all_new_lines()

                if entries:
                    print(f"[INFO] {len(entries)} yeni log satırı tespit edildi")
                    alerts = self.analyzer.analyze_batch(entries, self.config.batch_size)

                    if alerts:
                        self.alert_manager.send_all(alerts)

                time.sleep(self.config.interval_seconds)

            except Exception as e:
                print(f"[HATA] Beklenmeyen hata: {e}")
                time.sleep(5)

        print("[INFO] Uygulama sonlandırıldı")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Log Alarm LLM - Log analizi ve alarm sistemi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  # Tek seferlik analiz
  python -m src.main --once

  # Sürekli izleme
  python -m src.main --daemon

  # Web arayüzü
  python -m src.main --web
  python -m src.main --web --port 3000

  # Özel config dosyası
  python -m src.main --config /path/to/config.yaml --daemon
        """
    )

    parser.add_argument(
        "--config", "-c",
        help="Konfigürasyon dosyası yolu",
        default=None
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Tek seferlik analiz yap ve çık"
    )

    parser.add_argument(
        "--daemon", "-d",
        action="store_true",
        help="Sürekli izleme modunda çalış"
    )

    parser.add_argument(
        "--web", "-w",
        action="store_true",
        help="Web arayüzünü başlat"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Web sunucu portu (varsayılan: 8000)"
    )

    args = parser.parse_args()

    # En az bir mod seçilmeli
    if not args.once and not args.daemon and not args.web:
        parser.print_help()
        print("\n[HATA] --once, --daemon veya --web seçeneğinden birini belirtmelisiniz")
        sys.exit(1)

    try:
        if args.web:
            import uvicorn
            from .api import app as web_app
            print(f"[INFO] Web arayüzü başlatılıyor: http://localhost:{args.port}")
            uvicorn.run(web_app, host="0.0.0.0", port=args.port)
        else:
            app = LogAlarmApp(args.config)

            if args.once:
                alert_count = app.run_once()
                sys.exit(0 if alert_count == 0 else 1)
            else:
                app.run_daemon()

    except FileNotFoundError as e:
        print(f"[HATA] {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"[HATA] Konfigürasyon hatası: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[HATA] Beklenmeyen hata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
