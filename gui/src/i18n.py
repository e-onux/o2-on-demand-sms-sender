"""Translations for the desktop control panel."""

from __future__ import annotations

from string import Formatter
from typing import Any


LANGUAGES = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
    "pl": "Polski",
    "ru": "Русский",
}


TRANSLATIONS: dict[str, dict[str, str]] = {
    "app_title": {
        "tr": "O2 On-Demand SMS Kontrol Paneli",
        "en": "O2 On-Demand SMS Control Panel",
        "de": "O2 On-Demand SMS-Kontrollzentrum",
        "pl": "Panel sterowania O2 On-Demand SMS",
        "ru": "Панель управления O2 On-Demand SMS",
    },
    "header_title": {
        "tr": "O2 SMS Kontrol Paneli",
        "en": "O2 SMS Control Panel",
        "de": "O2 SMS-Kontrollzentrum",
        "pl": "Panel sterowania O2 SMS",
        "ru": "Панель управления O2 SMS",
    },
    "never": {"tr": "Henüz yok", "en": "Not yet", "de": "Noch nicht", "pl": "Jeszcze nie", "ru": "Пока нет"},
    "settings": {"tr": "Ayarlar", "en": "Settings", "de": "Einstellungen", "pl": "Ustawienia", "ru": "Настройки"},
    "language": {"tr": "Dil", "en": "Language", "de": "Sprache", "pl": "Język", "ru": "Язык"},
    "close_to_tray": {
        "tr": "Kapatınca sistem tepsisine küçült",
        "en": "Minimize to tray when closing",
        "de": "Beim Schließen in den Infobereich minimieren",
        "pl": "Minimalizuj do zasobnika przy zamykaniu",
        "ru": "Сворачивать в трей при закрытии",
    },
    "start_at_login": {
        "tr": "Oturum açılışında küçültülmüş başlat",
        "en": "Start minimized at login",
        "de": "Bei Anmeldung minimiert starten",
        "pl": "Uruchamiaj zminimalizowany po zalogowaniu",
        "ru": "Запускать свёрнутым при входе",
    },
    "minimize_to_tray": {
        "tr": "Şimdi sistem tepsisine küçült",
        "en": "Minimize to tray now",
        "de": "Jetzt in den Infobereich minimieren",
        "pl": "Minimalizuj teraz do zasobnika",
        "ru": "Свернуть в трей сейчас",
    },
    "show_window": {"tr": "Pencereyi Göster", "en": "Show Window", "de": "Fenster anzeigen", "pl": "Pokaż okno", "ru": "Показать окно"},
    "quit": {"tr": "Uygulamadan Çık", "en": "Quit Application", "de": "Anwendung beenden", "pl": "Zakończ aplikację", "ru": "Выйти из приложения"},
    "tray_unavailable": {
        "tr": "Sistem tepsisi bu ortamda kullanılamıyor.",
        "en": "The system tray is unavailable in this environment.",
        "de": "Der Infobereich ist in dieser Umgebung nicht verfügbar.",
        "pl": "Zasobnik systemowy jest niedostępny w tym środowisku.",
        "ru": "Системный трей недоступен в этой среде.",
    },
    "autostart_failed": {
        "tr": "Başlangıç ayarı kaydedilemedi: {error}",
        "en": "The startup setting could not be saved: {error}",
        "de": "Die Autostart-Einstellung konnte nicht gespeichert werden: {error}",
        "pl": "Nie można zapisać ustawienia autostartu: {error}",
        "ru": "Не удалось сохранить настройку автозапуска: {error}",
    },
    "git_loading": {"tr": "Git bilgisi okunuyor…", "en": "Reading Git status…", "de": "Git-Status wird gelesen…", "pl": "Odczytywanie stanu Git…", "ru": "Чтение состояния Git…"},
    "service_loading": {"tr": "Servis durumu okunuyor…", "en": "Reading service status…", "de": "Dienststatus wird gelesen…", "pl": "Odczytywanie stanu usługi…", "ru": "Чтение состояния службы…"},
    "actions": {"tr": "İşlemler", "en": "Actions", "de": "Aktionen", "pl": "Działania", "ru": "Действия"},
    "update_start": {"tr": "Güncelle + Başlat", "en": "Update + Start", "de": "Aktualisieren + Starten", "pl": "Aktualizuj + Uruchom", "ru": "Обновить + Запустить"},
    "git_pull": {"tr": "Git Pull", "en": "Git Pull", "de": "Git Pull", "pl": "Git Pull", "ru": "Git Pull"},
    "image_pull": {"tr": "İmaj Pull", "en": "Pull Image", "de": "Image laden", "pl": "Pobierz obraz", "ru": "Загрузить образ"},
    "service_start": {"tr": "Servisi Başlat", "en": "Start Service", "de": "Dienst starten", "pl": "Uruchom usługę", "ru": "Запустить службу"},
    "service_stop": {"tr": "Servisi Durdur", "en": "Stop Service", "de": "Dienst stoppen", "pl": "Zatrzymaj usługę", "ru": "Остановить службу"},
    "service_restart": {"tr": "Yeniden Başlat", "en": "Restart", "de": "Neu starten", "pl": "Uruchom ponownie", "ru": "Перезапустить"},
    "logs_refresh": {"tr": "Logları Yenile", "en": "Refresh Logs", "de": "Logs aktualisieren", "pl": "Odśwież logi", "ru": "Обновить журналы"},
    "refresh_now": {"tr": "Şimdi Yenile", "en": "Refresh Now", "de": "Jetzt aktualisieren", "pl": "Odśwież teraz", "ru": "Обновить сейчас"},
    "modem_actions": {"tr": "Modem İşlemleri", "en": "Modem Actions", "de": "Modemaktionen", "pl": "Działania modemu", "ru": "Действия модема"},
    "manual_sms": {"tr": "Manuel WEITER SMS Gönder", "en": "Send Manual WEITER SMS", "de": "WEITER-SMS manuell senden", "pl": "Wyślij ręcznie SMS WEITER", "ru": "Отправить WEITER вручную"},
    "clear_inbox": {"tr": "SMS Kutusunu Boşalt", "en": "Clear SMS Inbox", "de": "SMS-Postfach leeren", "pl": "Wyczyść skrzynkę SMS", "ru": "Очистить SMS"},
    "restart_modem": {"tr": "Modemi Yeniden Başlat", "en": "Restart Modem", "de": "Modem neu starten", "pl": "Uruchom modem ponownie", "ru": "Перезапустить модем"},
    "modem_note": {
        "tr": "Bu işlemler çalışan servisteki modeme doğrudan bağlanır ve önce onay ister.",
        "en": "These actions connect directly to the modem through the running service and require confirmation.",
        "de": "Diese Aktionen verbinden sich über den laufenden Dienst direkt mit dem Modem und erfordern eine Bestätigung.",
        "pl": "Te działania łączą się bezpośrednio z modemem przez uruchomioną usługę i wymagają potwierdzenia.",
        "ru": "Эти действия подключаются к модему через работающую службу и требуют подтверждения.",
    },
    "last_sms": {"tr": "Son SMS", "en": "Last SMS", "de": "Letzte SMS", "pl": "Ostatni SMS", "ru": "Последнее SMS"},
    "today_sent": {"tr": "Bugün gönderilen", "en": "Sent today", "de": "Heute gesendet", "pl": "Wysłano dzisiaj", "ru": "Отправлено сегодня"},
    "total_sent": {"tr": "Toplam gönderilen", "en": "Total sent", "de": "Insgesamt gesendet", "pl": "Wysłano łącznie", "ru": "Всего отправлено"},
    "today_usage": {"tr": "Bugünkü kullanım (GB)", "en": "Today's usage (GB)", "de": "Heutige Nutzung (GB)", "pl": "Dzisiejsze użycie (GB)", "ru": "Использование сегодня (ГБ)"},
    "last_check": {"tr": "Son kontrol", "en": "Last check", "de": "Letzte Prüfung", "pl": "Ostatnia kontrola", "ru": "Последняя проверка"},
    "current_details": {"tr": "Güncel Bilgiler", "en": "Current Details", "de": "Aktuelle Details", "pl": "Aktualne informacje", "ru": "Текущие сведения"},
    "last_reason": {"tr": "Son SMS sebebi:", "en": "Last SMS reason:", "de": "Grund der letzten SMS:", "pl": "Powód ostatniego SMS-a:", "ru": "Причина последнего SMS:"},
    "last_result": {"tr": "Son kontrol sonucu:", "en": "Last check result:", "de": "Ergebnis der letzten Prüfung:", "pl": "Wynik ostatniej kontroli:", "ru": "Результат последней проверки:"},
    "threshold_status": {"tr": "Eşik durumu:", "en": "Threshold status:", "de": "Schwellenwertstatus:", "pl": "Stan progu:", "ru": "Состояние порога:"},
    "last_error": {"tr": "Son hata:", "en": "Last error:", "de": "Letzter Fehler:", "pl": "Ostatni błąd:", "ru": "Последняя ошибка:"},
    "recent_events": {"tr": "Son Olaylar", "en": "Recent Events", "de": "Letzte Ereignisse", "pl": "Ostatnie zdarzenia", "ru": "Последние события"},
    "copy_events": {"tr": "Olayları Kopyala", "en": "Copy Events", "de": "Ereignisse kopieren", "pl": "Kopiuj zdarzenia", "ru": "Копировать события"},
    "clear_events": {"tr": "Olayları Temizle", "en": "Clear Events", "de": "Ereignisse löschen", "pl": "Wyczyść zdarzenia", "ru": "Очистить события"},
    "time": {"tr": "Zaman", "en": "Time", "de": "Zeit", "pl": "Czas", "ru": "Время"},
    "event": {"tr": "Olay", "en": "Event", "de": "Ereignis", "pl": "Zdarzenie", "ru": "Событие"},
    "description": {"tr": "Açıklama", "en": "Description", "de": "Beschreibung", "pl": "Opis", "ru": "Описание"},
    "logs": {"tr": "İşlem / Docker Logları", "en": "Action / Docker Logs", "de": "Aktionen / Docker-Logs", "pl": "Działania / logi Dockera", "ru": "Действия / журналы Docker"},
    "ready": {"tr": "Hazır", "en": "Ready", "de": "Bereit", "pl": "Gotowe", "ru": "Готово"},
    "command_not_found": {"tr": "Komut bulunamadı: {command}", "en": "Command not found: {command}", "de": "Befehl nicht gefunden: {command}", "pl": "Nie znaleziono polecenia: {command}", "ru": "Команда не найдена: {command}"},
    "command_timeout": {"tr": "Komut {seconds} saniye içinde tamamlanmadı.", "en": "The command did not finish within {seconds} seconds.", "de": "Der Befehl wurde nicht innerhalb von {seconds} Sekunden abgeschlossen.", "pl": "Polecenie nie zakończyło się w ciągu {seconds} sekund.", "ru": "Команда не завершилась за {seconds} секунд."},
    "command_failed": {"tr": "Komut çalıştırılamadı: {error}", "en": "The command could not be executed: {error}", "de": "Der Befehl konnte nicht ausgeführt werden: {error}", "pl": "Nie można wykonać polecenia: {error}", "ru": "Не удалось выполнить команду: {error}"},
    "no_sms_record": {"tr": "Henüz SMS kaydı yok.", "en": "No SMS has been recorded yet.", "de": "Noch keine SMS erfasst.", "pl": "Nie zapisano jeszcze żadnego SMS-a.", "ru": "SMS пока не зарегистрированы."},
    "success": {"tr": "Başarılı", "en": "Successful", "de": "Erfolgreich", "pl": "Powodzenie", "ru": "Успешно"},
    "sms_sent_suffix": {"tr": "SMS gönderildi", "en": "SMS sent", "de": "SMS gesendet", "pl": "SMS wysłany", "ru": "SMS отправлено"},
    "sms_not_needed": {"tr": "SMS gerekmedi", "en": "No SMS needed", "de": "Keine SMS erforderlich", "pl": "SMS nie był potrzebny", "ru": "SMS не требовалось"},
    "error": {"tr": "Hata", "en": "Error", "de": "Fehler", "pl": "Błąd", "ru": "Ошибка"},
    "checking": {"tr": "Kontrol devam ediyor", "en": "Check in progress", "de": "Prüfung läuft", "pl": "Trwa kontrola", "ru": "Идёт проверка"},
    "no_check": {"tr": "Henüz kontrol kaydı yok", "en": "No check has been recorded yet", "de": "Noch keine Prüfung erfasst", "pl": "Nie zapisano jeszcze kontroli", "ru": "Проверки пока не зарегистрированы"},
    "no_initial_check": {
        "tr": "Servis ilk başarılı kontrolünü henüz tamamlamadı.",
        "en": "The service has not completed its first successful check yet.",
        "de": "Der Dienst hat seine erste erfolgreiche Prüfung noch nicht abgeschlossen.",
        "pl": "Usługa nie ukończyła jeszcze pierwszej pomyślnej kontroli.",
        "ru": "Служба ещё не завершила первую успешную проверку.",
    },
    "next_threshold": {
        "tr": "Son SMS başlangıcı {baseline:.2f} GiB; sonraki eşik {next_threshold:.2f} GiB.",
        "en": "Last SMS baseline {baseline:.2f} GiB; next threshold {next_threshold:.2f} GiB.",
        "de": "Ausgangswert der letzten SMS {baseline:.2f} GiB; nächste Schwelle {next_threshold:.2f} GiB.",
        "pl": "Poziom bazowy ostatniego SMS-a {baseline:.2f} GiB; następny próg {next_threshold:.2f} GiB.",
        "ru": "Базовый уровень последнего SMS: {baseline:.2f} GiB; следующий порог: {next_threshold:.2f} GiB.",
    },
    "check_prefix": {"tr": "Kontrol", "en": "Check", "de": "Prüfung", "pl": "Kontrola", "ru": "Проверка"},
    "manual_prefix": {"tr": "Manuel işlem", "en": "Manual action", "de": "Manuelle Aktion", "pl": "Działanie ręczne", "ru": "Ручное действие"},
    "none": {"tr": "Yok", "en": "None", "de": "Keine", "pl": "Brak", "ru": "Нет"},
    "event_sms_sent": {"tr": "SMS gönderildi", "en": "SMS sent", "de": "SMS gesendet", "pl": "Wysłano SMS", "ru": "SMS отправлено"},
    "event_check_completed": {"tr": "Kontrol tamamlandı", "en": "Check completed", "de": "Prüfung abgeschlossen", "pl": "Kontrola zakończona", "ru": "Проверка завершена"},
    "event_check_failed": {"tr": "Kontrol hatası", "en": "Check failed", "de": "Prüfung fehlgeschlagen", "pl": "Błąd kontroli", "ru": "Ошибка проверки"},
    "event_usage_reset": {"tr": "Sayaç sıfırlandı", "en": "Counter reset", "de": "Zähler zurückgesetzt", "pl": "Licznik wyzerowany", "ru": "Счётчик сброшен"},
    "event_baseline_reset": {"tr": "Eşik sıfırlandı", "en": "Baseline reset", "de": "Ausgangswert zurückgesetzt", "pl": "Poziom bazowy wyzerowany", "ru": "Базовый уровень сброшен"},
    "event_inbox_cleared": {"tr": "SMS kutusu boşaltıldı", "en": "SMS inbox cleared", "de": "SMS-Postfach geleert", "pl": "Skrzynka SMS wyczyszczona", "ru": "SMS очищены"},
    "event_modem_restarted": {"tr": "Modem yeniden başlatıldı", "en": "Modem restarted", "de": "Modem neu gestartet", "pl": "Modem uruchomiony ponownie", "ru": "Модем перезапущен"},
    "event_manual_failed": {"tr": "Manuel işlem hatası", "en": "Manual action failed", "de": "Manuelle Aktion fehlgeschlagen", "pl": "Błąd działania ręcznego", "ru": "Ошибка ручного действия"},
    "event_unknown": {"tr": "bilinmiyor", "en": "unknown", "de": "unbekannt", "pl": "nieznane", "ru": "неизвестно"},
    "event_usage": {"tr": "Kullanım: {usage}", "en": "Usage: {usage}", "de": "Nutzung: {usage}", "pl": "Użycie: {usage}", "ru": "Использование: {usage}"},
    "runtime_check_sent": {"tr": "SMS gönderildi.", "en": "SMS was sent.", "de": "SMS wurde gesendet.", "pl": "SMS został wysłany.", "ru": "SMS отправлено."},
    "runtime_check_no_sms": {"tr": "SMS gönderme eşiğine henüz ulaşılmadı.", "en": "The SMS threshold has not been reached yet.", "de": "Die SMS-Schwelle wurde noch nicht erreicht.", "pl": "Próg wysłania SMS-a nie został jeszcze osiągnięty.", "ru": "Порог отправки SMS ещё не достигнут."},
    "runtime_counter_reset": {"tr": "Günlük veri sayacı sıfırlandı.", "en": "The daily data counter was reset.", "de": "Der tägliche Datenzähler wurde zurückgesetzt.", "pl": "Dzienny licznik danych został wyzerowany.", "ru": "Суточный счётчик данных сброшен."},
    "runtime_baseline_reset": {"tr": "SMS veri eşiği başlangıç değeri sıfırlandı.", "en": "The SMS usage baseline was reset.", "de": "Der Ausgangswert für die SMS-Schwelle wurde zurückgesetzt.", "pl": "Poziom bazowy progu SMS został wyzerowany.", "ru": "Базовый уровень порога SMS сброшен."},
    "runtime_inbox_cleared": {"tr": "SMS kutusu temizlendi; {count} mesaj silindi.", "en": "The SMS inbox was cleared; {count} messages deleted.", "de": "Das SMS-Postfach wurde geleert; {count} Nachrichten gelöscht.", "pl": "Skrzynka SMS została wyczyszczona; usunięto {count} wiadomości.", "ru": "SMS очищены; удалено сообщений: {count}."},
    "runtime_modem_restarted": {"tr": "Modem yeniden başlatma isteği gönderildi.", "en": "The modem restart request was sent.", "de": "Die Anforderung zum Neustart des Modems wurde gesendet.", "pl": "Wysłano żądanie ponownego uruchomienia modemu.", "ru": "Запрос на перезапуск модема отправлен."},
    "runtime_manual_sms": {"tr": "Kontrol panelinden manuel olarak gönderildi.", "en": "Sent manually from the control panel.", "de": "Manuell über das Kontrollzentrum gesendet.", "pl": "Wysłano ręcznie z panelu sterowania.", "ru": "Отправлено вручную из панели управления."},
    "runtime_trigger_exhausted": {"tr": "O2 yüksek hız veri hacmi tükendi SMS'i alındı.", "en": "O2 high-speed allowance exhausted SMS received.", "de": "O2-SMS zum verbrauchten Highspeed-Datenvolumen empfangen.", "pl": "Odebrano SMS O2 o wyczerpaniu pakietu szybkich danych.", "ru": "Получено SMS O2 об исчерпании высокоскоростного трафика."},
    "runtime_trigger_80": {"tr": "O2 yüksek hız veri hacmi %80 SMS'i alındı.", "en": "O2 80% high-speed allowance SMS received.", "de": "O2-SMS zu 80 % des Highspeed-Datenvolumens empfangen.", "pl": "Odebrano SMS O2 o wykorzystaniu 80% szybkich danych.", "ru": "Получено SMS O2 об использовании 80% высокоскоростного трафика."},
    "runtime_threshold": {"tr": "{threshold:.2f} GiB yeni veri kullanım eşiği aşıldı.", "en": "The new-data threshold of {threshold:.2f} GiB was exceeded.", "de": "Die Schwelle von {threshold:.2f} GiB neuer Datennutzung wurde überschritten.", "pl": "Przekroczono próg {threshold:.2f} GiB nowego użycia danych.", "ru": "Превышен порог нового трафика {threshold:.2f} GiB."},
    "local_changes": {"tr": "{count} yerel değişiklik", "en": "{count} local changes", "de": "{count} lokale Änderungen", "pl": "{count} lokalnych zmian", "ru": "локальных изменений: {count}"},
    "git_unavailable": {"tr": "Git durumu okunamadı", "en": "Git status unavailable", "de": "Git-Status nicht verfügbar", "pl": "Stan Git jest niedostępny", "ru": "Состояние Git недоступно"},
    "docker_unavailable": {"tr": "● Docker Engine erişilemiyor", "en": "● Docker Engine unavailable", "de": "● Docker Engine nicht erreichbar", "pl": "● Docker Engine jest niedostępny", "ru": "● Docker Engine недоступен"},
    "service_missing": {"tr": "● Servis henüz oluşturulmadı", "en": "● Service has not been created", "de": "● Dienst wurde noch nicht erstellt", "pl": "● Usługa nie została utworzona", "ru": "● Служба ещё не создана"},
    "service_running": {"tr": "● Servis çalışıyor{health} - {detail}", "en": "● Service running{health} - {detail}", "de": "● Dienst läuft{health} - {detail}", "pl": "● Usługa działa{health} - {detail}", "ru": "● Служба работает{health} - {detail}"},
    "service_state": {"tr": "● Servis {state} - {detail}", "en": "● Service {state} - {detail}", "de": "● Dienst {state} - {detail}", "pl": "● Usługa {state} - {detail}", "ru": "● Служба {state} - {detail}"},
    "wait_for_command": {"tr": "Önce devam eden işlemin tamamlanmasını bekleyin.", "en": "Wait for the current action to finish first.", "de": "Warten Sie zuerst, bis die aktuelle Aktion abgeschlossen ist.", "pl": "Najpierw zaczekaj na zakończenie bieżącego działania.", "ru": "Сначала дождитесь завершения текущего действия."},
    "action_running": {"tr": "{title} çalışıyor…", "en": "{title} is running…", "de": "{title} wird ausgeführt…", "pl": "Trwa: {title}…", "ru": "Выполняется: {title}…"},
    "no_output": {"tr": "(çıktı yok)", "en": "(no output)", "de": "(keine Ausgabe)", "pl": "(brak danych wyjściowych)", "ru": "(нет вывода)"},
    "action_completed": {"tr": "{title} tamamlandı.", "en": "{title} completed.", "de": "{title} abgeschlossen.", "pl": "Zakończono: {title}.", "ru": "Завершено: {title}."},
    "action_failed": {"tr": "{title} başarısız oldu (kod: {code}). Ayrıntı loglarda.", "en": "{title} failed (code: {code}). See the logs for details.", "de": "{title} fehlgeschlagen (Code: {code}). Details stehen in den Logs.", "pl": "{title} nie powiodło się (kod: {code}). Szczegóły w logach.", "ru": "Ошибка: {title} (код: {code}). Подробности в журнале."},
    "op_update_start": {"tr": "Güncelleme ve başlatma", "en": "Update and start", "de": "Aktualisieren und starten", "pl": "Aktualizacja i uruchamianie", "ru": "Обновление и запуск"},
    "op_image_pull": {"tr": "Docker imajını çekme", "en": "Pull Docker image", "de": "Docker-Image laden", "pl": "Pobieranie obrazu Dockera", "ru": "Загрузка образа Docker"},
    "op_start": {"tr": "Servisi başlatma", "en": "Start service", "de": "Dienst starten", "pl": "Uruchamianie usługi", "ru": "Запуск службы"},
    "op_stop": {"tr": "Servisi durdurma", "en": "Stop service", "de": "Dienst stoppen", "pl": "Zatrzymywanie usługi", "ru": "Остановка службы"},
    "op_restart": {"tr": "Servisi yeniden başlatma", "en": "Restart service", "de": "Dienst neu starten", "pl": "Ponowne uruchamianie usługi", "ru": "Перезапуск службы"},
    "op_logs": {"tr": "Docker loglarını yükleme", "en": "Load Docker logs", "de": "Docker-Logs laden", "pl": "Wczytywanie logów Dockera", "ru": "Загрузка журналов Docker"},
    "manual_confirm_title": {"tr": "Manuel SMS gönderimi", "en": "Manual SMS", "de": "Manuelle SMS", "pl": "Ręczny SMS", "ru": "Ручное SMS"},
    "manual_confirm": {"tr": "80112 numarasına şimdi WEITER SMS'i gönderilecek. Devam edilsin mi?", "en": "Send a WEITER SMS to 80112 now?", "de": "Jetzt eine WEITER-SMS an 80112 senden?", "pl": "Wysłać teraz SMS WEITER na numer 80112?", "ru": "Отправить сейчас SMS WEITER на номер 80112?"},
    "op_manual_sms": {"tr": "Manuel WEITER SMS gönderimi", "en": "Send manual WEITER SMS", "de": "WEITER-SMS manuell senden", "pl": "Ręczne wysyłanie SMS-a WEITER", "ru": "Ручная отправка SMS WEITER"},
    "clear_inbox_title": {"tr": "SMS kutusunu boşalt", "en": "Clear SMS inbox", "de": "SMS-Postfach leeren", "pl": "Wyczyść skrzynkę SMS", "ru": "Очистить SMS"},
    "clear_inbox_confirm": {"tr": "Modemin SMS kutusundaki tüm mesajlar kalıcı olarak silinecek. Devam edilsin mi?", "en": "All messages in the modem SMS inbox will be permanently deleted. Continue?", "de": "Alle Nachrichten im SMS-Postfach des Modems werden dauerhaft gelöscht. Fortfahren?", "pl": "Wszystkie wiadomości w skrzynce SMS modemu zostaną trwale usunięte. Kontynuować?", "ru": "Все сообщения в SMS-хранилище модема будут удалены безвозвратно. Продолжить?"},
    "op_clear_inbox": {"tr": "SMS kutusunu temizleme", "en": "Clear SMS inbox", "de": "SMS-Postfach leeren", "pl": "Czyszczenie skrzynki SMS", "ru": "Очистка SMS"},
    "restart_modem_title": {"tr": "Modemi yeniden başlat", "en": "Restart modem", "de": "Modem neu starten", "pl": "Uruchom modem ponownie", "ru": "Перезапустить модем"},
    "restart_modem_confirm": {"tr": "Modem şimdi yeniden başlatılacak. İnternet bağlantısı birkaç dakika kesilebilir. Emin misiniz?", "en": "The modem will restart now. The internet connection may be interrupted for a few minutes. Are you sure?", "de": "Das Modem wird jetzt neu gestartet. Die Internetverbindung kann für einige Minuten unterbrochen werden. Sind Sie sicher?", "pl": "Modem zostanie teraz uruchomiony ponownie. Połączenie internetowe może zostać przerwane na kilka minut. Czy na pewno kontynuować?", "ru": "Модем будет перезапущен. Подключение к интернету может прерваться на несколько минут. Вы уверены?"},
    "op_restart_modem": {"tr": "Modemi yeniden başlatma", "en": "Restart modem", "de": "Modem neu starten", "pl": "Ponowne uruchamianie modemu", "ru": "Перезапуск модема"},
    "no_events_to_copy": {"tr": "Kopyalanacak olay kaydı yok.", "en": "There are no events to copy.", "de": "Es gibt keine Ereignisse zum Kopieren.", "pl": "Brak zdarzeń do skopiowania.", "ru": "Нет событий для копирования."},
    "events_copied": {"tr": "{count} olay panoya kopyalandı.", "en": "{count} events copied to the clipboard.", "de": "{count} Ereignisse in die Zwischenablage kopiert.", "pl": "Skopiowano {count} zdarzeń do schowka.", "ru": "Событий скопировано в буфер: {count}."},
    "clear_events_title": {"tr": "Olay geçmişini temizle", "en": "Clear event history", "de": "Ereignisverlauf löschen", "pl": "Wyczyść historię zdarzeń", "ru": "Очистить историю событий"},
    "clear_events_confirm": {"tr": "Kaydedilmiş tüm olaylar kalıcı olarak silinecek. Devam edilsin mi?", "en": "All recorded events will be permanently deleted. Continue?", "de": "Alle aufgezeichneten Ereignisse werden dauerhaft gelöscht. Fortfahren?", "pl": "Wszystkie zapisane zdarzenia zostaną trwale usunięte. Kontynuować?", "ru": "Все записанные события будут удалены безвозвратно. Продолжить?"},
    "op_clear_events": {"tr": "Olay geçmişini temizleme", "en": "Clear event history", "de": "Ereignisverlauf löschen", "pl": "Czyszczenie historii zdarzeń", "ru": "Очистка истории событий"},
    "events_cleared": {"tr": "Olay geçmişi temizlendi.", "en": "Event history cleared.", "de": "Ereignisverlauf gelöscht.", "pl": "Historia zdarzeń została wyczyszczona.", "ru": "История событий очищена."},
    "network_chart": {"tr": "Bağlantı: ping ve indirme hızı", "en": "Connection: ping and download speed", "de": "Verbindung: Ping und Download-Geschwindigkeit", "pl": "Połączenie: ping i prędkość pobierania", "ru": "Соединение: пинг и скорость загрузки"},
    "chart_summary": {"tr": "Son ping: {ping} ms · Son hız: {speed} Mbit/s", "en": "Last ping: {ping} ms · Last speed: {speed} Mbit/s", "de": "Letzter Ping: {ping} ms · Letzte Geschwindigkeit: {speed} Mbit/s", "pl": "Ostatni ping: {ping} ms · Ostatnia prędkość: {speed} Mbit/s", "ru": "Последний пинг: {ping} мс · Последняя скорость: {speed} Мбит/с"},
    "chart_window_1h": {"tr": "1 saat", "en": "1 hour", "de": "1 Stunde", "pl": "1 godzina", "ru": "1 час"},
    "chart_window_6h": {"tr": "6 saat", "en": "6 hours", "de": "6 Stunden", "pl": "6 godzin", "ru": "6 часов"},
    "chart_window_24h": {"tr": "24 saat", "en": "24 hours", "de": "24 Stunden", "pl": "24 godziny", "ru": "24 часа"},
    "chart_now": {"tr": "şimdi", "en": "now", "de": "jetzt", "pl": "teraz", "ru": "сейчас"},
    "chart_no_data": {"tr": "Henüz ölçüm yok.", "en": "No measurements yet.", "de": "Noch keine Messungen.", "pl": "Brak pomiarów.", "ru": "Измерений пока нет."},
    "connection_status": {"tr": "Bağlantı durumu", "en": "Connection status", "de": "Verbindungsstatus", "pl": "Stan połączenia", "ru": "Состояние соединения"},
    "conn_unknown": {"tr": "Henüz değerlendirilmedi.", "en": "Not evaluated yet.", "de": "Noch nicht bewertet.", "pl": "Jeszcze nie oceniono.", "ru": "Ещё не оценено."},
    "conn_healthy": {"tr": "Normal.", "en": "Normal.", "de": "Normal.", "pl": "Normalne.", "ru": "Нормальное."},
    "conn_unmeasured": {"tr": "Ölçülemiyor: worker internete ulaşamıyor (DNS/ağ). Bu durumda otomatik işlem yapılmaz.", "en": "Cannot measure: the worker cannot reach the internet (DNS/network). No automatic action is taken.", "de": "Messung nicht möglich: Der Worker erreicht das Internet nicht (DNS/Netzwerk). Es wird keine automatische Aktion ausgeführt.", "pl": "Brak pomiaru: worker nie ma dostępu do internetu (DNS/sieć). Żadne automatyczne działanie nie jest wykonywane.", "ru": "Измерение невозможно: worker не может выйти в интернет (DNS/сеть). Автоматические действия не выполняются."},
    "conn_degraded": {"tr": "Yavaş görünüyor; doğrulanıyor.", "en": "Looks slow; confirming.", "de": "Wirkt langsam; wird bestätigt.", "pl": "Wygląda na wolne; trwa potwierdzanie.", "ru": "Похоже на медленное; проверяется."},
    "conn_sms_wait": {"tr": "Yavaş; SMS gönderildi, {time} itibarıyla tekrar ölçülecek.", "en": "Slow; SMS sent, re-measuring from {time}.", "de": "Langsam; SMS gesendet, erneute Messung ab {time}.", "pl": "Wolne; SMS wysłany, ponowny pomiar od {time}.", "ru": "Медленное; SMS отправлено, повторное измерение с {time}."},
    "conn_restart_wait": {"tr": "Bu dönemde {count} otomatik yeniden başlatma; sonraki en erken {time}.", "en": "{count} automatic restarts in this episode; next one no earlier than {time}.", "de": "{count} automatische Neustarts in dieser Phase; nächster frühestens {time}.", "pl": "{count} automatycznych restartów w tym okresie; następny najwcześniej {time}.", "ru": "Автоматических перезапусков в этом эпизоде: {count}; следующий не ранее {time}."},
    "event_connection_slow_sms": {"tr": "Yavaş bağlantı", "en": "Slow connection", "de": "Langsame Verbindung", "pl": "Wolne połączenie", "ru": "Медленное соединение"},
    "event_modem_auto_restarted": {"tr": "Otomatik yeniden başlatma", "en": "Automatic restart", "de": "Automatischer Neustart", "pl": "Automatyczny restart", "ru": "Автоматический перезапуск"},
    "event_connection_recovered": {"tr": "Bağlantı düzeldi", "en": "Connection recovered", "de": "Verbindung erholt", "pl": "Połączenie przywrócone", "ru": "Соединение восстановлено"},
    "event_restart_limit_reached": {"tr": "Yeniden başlatma sınırı", "en": "Restart limit", "de": "Neustart-Limit", "pl": "Limit restartów", "ru": "Лимит перезапусков"},
    "event_watchdog_failed": {"tr": "Bağlantı izleme hatası", "en": "Connection watchdog error", "de": "Fehler der Verbindungsüberwachung", "pl": "Błąd monitora połączenia", "ru": "Ошибка контроля соединения"},
    "runtime_connection_slow_sms": {"tr": "Bağlantı yavaş; önce WEITER SMS'i gönderildi.", "en": "Connection slow; the WEITER SMS was sent first.", "de": "Verbindung langsam; zuerst wurde die WEITER-SMS gesendet.", "pl": "Połączenie wolne; najpierw wysłano SMS WEITER.", "ru": "Соединение медленное; сначала отправлено SMS WEITER."},
    "runtime_modem_auto_restarted": {"tr": "SMS'ten sonra da yavaş; modem otomatik yeniden başlatıldı.", "en": "Still slow after the SMS; the modem was restarted automatically.", "de": "Auch nach der SMS langsam; das Modem wurde automatisch neu gestartet.", "pl": "Nadal wolne po SMS; modem został automatycznie uruchomiony ponownie.", "ru": "После SMS всё ещё медленно; модем перезапущен автоматически."},
    "runtime_connection_recovered": {"tr": "Bağlantı yeniden normal hızda.", "en": "The connection is back to normal speed.", "de": "Die Verbindung hat wieder normale Geschwindigkeit.", "pl": "Połączenie wróciło do normalnej prędkości.", "ru": "Скорость соединения снова в норме."},
    "runtime_restart_limit_reached": {"tr": "Günlük otomatik yeniden başlatma sınırına ulaşıldı; bekleniyor.", "en": "Daily automatic restart limit reached; waiting.", "de": "Tägliches Limit für automatische Neustarts erreicht; es wird gewartet.", "pl": "Osiągnięto dzienny limit automatycznych restartów; oczekiwanie.", "ru": "Достигнут дневной лимит автоматических перезапусков; ожидание."},
    "refreshed": {"tr": "Bilgiler yenilendi.", "en": "Information refreshed.", "de": "Informationen aktualisiert.", "pl": "Informacje odświeżone.", "ru": "Информация обновлена."},
}


def translate(language: str, key: str, **values: Any) -> str:
    """Return a translated string with English as the fallback language."""
    choices = TRANSLATIONS.get(key)
    if choices is None:
        return key
    template = choices.get(language, choices["en"])
    return template.format(**values)


def validate_translations() -> list[str]:
    """Return missing entries or placeholder mismatches for build checks."""
    missing: list[str] = []
    for key, choices in TRANSLATIONS.items():
        expected_fields = {
            field_name
            for _, field_name, _, _ in Formatter().parse(choices["en"])
            if field_name is not None
        }
        for language in LANGUAGES:
            if not choices.get(language):
                missing.append(f"{key}:{language}")
                continue
            actual_fields = {
                field_name
                for _, field_name, _, _ in Formatter().parse(choices[language])
                if field_name is not None
            }
            if actual_fields != expected_fields:
                missing.append(f"{key}:{language}:placeholders")
    return missing
