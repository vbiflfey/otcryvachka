import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os
import sys
import json
import threading
import time
import winreg

CONFIG_FILE = "config.json"

class WatchdogApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Открывашка - Страж процессов")
        self.root.geometry("950x650")
        self.root.configure(bg='#f0f0f0')
        
        self.apps = []
        self.running = True
        self.watch_thread = None
        self.autostart_enabled = False
        
        self.load_config()
        self.create_widgets()
        self.start_watchdog()
        self.check_autostart_status()
        
    def create_widgets(self):
        # Заголовок
        title_frame = tk.Frame(self.root, bg='#4CAF50', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="🛡️ Открывашка - Автоматический страж процессов", 
                font=("Segoe UI", 16, "bold"), bg='#4CAF50', fg="white").pack(pady=15)
        
        # Верхняя панель
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="➕ Добавить", command=self.add_app, 
                 bg='#4CAF50', fg="white", font=("Segoe UI", 10, "bold"), padx=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="❌ Удалить", command=self.remove_app, 
                 bg='#f44336', fg="white", font=("Segoe UI", 10, "bold"), padx=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="▶️ Запустить все", command=self.start_all_apps, 
                 bg='#2196F3', fg="white", font=("Segoe UI", 10, "bold"), padx=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="🔄 Обновить", command=self.update_statuses, 
                 bg='#FF9800', fg="white", font=("Segoe UI", 10, "bold"), padx=15).pack(side=tk.LEFT, padx=5)
        
        # Галочка автозапуска
        self.autostart_var = tk.BooleanVar(value=self.autostart_enabled)
        autostart_check = tk.Checkbutton(button_frame, text="⚡ Автозапуск с Windows", 
                                         variable=self.autostart_var, command=self.toggle_autostart,
                                         bg='#f0f0f0', font=("Segoe UI", 10))
        autostart_check.pack(side=tk.LEFT, padx=20)
        
        # Таблица
        table_frame = tk.Frame(self.root, bg='#f0f0f0')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Название", "Путь к файлу", "Отслеживаемый процесс", "Статус", "Последний запуск")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        widths = {"Название": 150, "Путь к файлу": 350, "Отслеживаемый процесс": 180, "Статус": 120, "Последний запуск": 140}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col])
        
        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Статус
        self.status_label = tk.Label(self.root, text="🟢 Статус: Активно слежение", 
                                     font=("Segoe UI", 9), bg='#f0f0f0', anchor=tk.W, padx=10, pady=8)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.update_statuses()
        
    def add_app(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить приложение")
        dialog.geometry("550x350")
        dialog.configure(bg='#f0f0f0')
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 1. Выбор файла для запуска
        tk.Label(dialog, text="📁 Выберите файл для запуска:", font=("Segoe UI", 10, "bold"), 
                bg='#f0f0f0').pack(pady=(20,5))
        
        file_frame = tk.Frame(dialog, bg='#f0f0f0')
        file_frame.pack(pady=5)
        
        file_path_var = tk.StringVar()
        file_entry = tk.Entry(file_frame, textvariable=file_path_var, width=45)
        file_entry.pack(side=tk.LEFT, padx=5)
        
        def browse_file():
            path = filedialog.askopenfilename(
                title="Выберите файл для запуска",
                filetypes=[("Исполняемые файлы", "*.exe *.bat *.cmd *.ps1"), ("Все файлы", "*.*")]
            )
            if path:
                file_path_var.set(path)
                # Автоматически предлагаем имя процесса для отслеживания
                ext = os.path.splitext(path)[1].lower()
                if ext == '.exe':
                    process_var.set(os.path.basename(path))
                elif ext in ['.bat', '.cmd']:
                    # Для bat предлагаем выбрать процесс отдельно
                    process_var.set("")
        
        tk.Button(file_frame, text="Обзор", command=browse_file, bg='#2196F3', fg='white', padx=10).pack(side=tk.LEFT)
        
        # 2. Отслеживаемый процесс (с обзором)
        tk.Label(dialog, text="🔍 Отслеживаемый процесс (что проверять на запуск):", 
                font=("Segoe UI", 10, "bold"), bg='#f0f0f0').pack(pady=(15,5))
        tk.Label(dialog, text="Укажите имя процесса (например: notepad.exe) или выберите файл", 
                font=("Segoe UI", 8), bg='#f0f0f0', fg='gray').pack()
        
        process_frame = tk.Frame(dialog, bg='#f0f0f0')
        process_frame.pack(pady=5)
        
        process_var = tk.StringVar()
        process_entry = tk.Entry(process_frame, textvariable=process_var, width=45)
        process_entry.pack(side=tk.LEFT, padx=5)
        
        def browse_process():
            # Выбираем exe файл и берем только его имя
            proc_path = filedialog.askopenfilename(
                title="Выберите программу для отслеживания (возьмется только имя файла)",
                filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")]
            )
            if proc_path:
                # Берем только имя файла (например: myapp.exe)
                proc_name = os.path.basename(proc_path)
                process_var.set(proc_name)
                # Показываем подсказку
                process_entry.config(fg='green')
                # Возвращаем цвет через 2 секунды
                dialog.after(2000, lambda: process_entry.config(fg='black'))
        
        tk.Button(process_frame, text="Обзор", command=browse_process, bg='#FF9800', fg='white', padx=10).pack(side=tk.LEFT)
        
        # Подсказка
        tk.Label(dialog, text="💡 Для bat/cmd файлов: укажите процесс, который они запускают (например: chrome.exe)", 
                font=("Segoe UI", 8), bg='#f0f0f0', fg='#666').pack(pady=(10,0))
        
        def save():
            file_path = file_path_var.get().strip()
            if not file_path or not os.path.exists(file_path):
                messagebox.showerror("Ошибка", "Выберите существующий файл для запуска!")
                return
            
            app_name = os.path.splitext(os.path.basename(file_path))[0]
            track_process = process_var.get().strip()
            
            # Если для bat-файла не указан процесс для отслеживания
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.bat', '.cmd'] and not track_process:
                # Пробуем угадать по имени
                track_process = f"{app_name}.exe"
                if not messagebox.askyesno("Вопрос", 
                    f"Вы не указали процесс для отслеживания.\n\n"
                    f"Буду отслеживать '{track_process}'.\n"
                    f"Если это неверно, программа не будет правильно перезапускать приложение.\n\n"
                    f"Продолжить с этим процессом?"):
                    return
            
            if not track_process:
                track_process = os.path.basename(file_path)
            
            self.apps.append({
                "name": app_name,
                "path": file_path,
                "track_process": track_process,
                "last_start": "Никогда"
            })
            
            self.save_config()
            self.update_statuses()
            dialog.destroy()
            messagebox.showinfo("Успех", 
                f"✅ '{app_name}' добавлен!\n\n"
                f"📂 Запускаемый файл: {os.path.basename(file_path)}\n"
                f"🔍 Отслеживается процесс: {track_process}")
        
        # Кнопки внизу
        button_frame_dialog = tk.Frame(dialog, bg='#f0f0f0')
        button_frame_dialog.pack(pady=20)
        
        tk.Button(button_frame_dialog, text="✅ Добавить", command=save, bg='#4CAF50', fg='white', 
                 font=("Segoe UI", 10, "bold"), padx=20).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame_dialog, text="❌ Отмена", command=dialog.destroy, bg='#999', fg='white', 
                 font=("Segoe UI", 10), padx=20).pack(side=tk.LEFT, padx=10)
    
    def remove_app(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите приложение!")
            return
        
        item = self.tree.item(selected[0])
        app_name = item['values'][0]
        
        if messagebox.askyesno("Подтверждение", f"Удалить '{app_name}'?"):
            for i, app in enumerate(self.apps):
                if app['name'] == app_name:
                    del self.apps[i]
                    break
            
            self.save_config()
            self.update_statuses()
    
    def start_all_apps(self):
        if not self.apps:
            messagebox.showinfo("Инфо", "Нет приложений для запуска")
            return
        
        for app in self.apps:
            self.start_app(app)
        self.update_statuses()
        messagebox.showinfo("Выполнено", "✅ Все приложения запущены!")
    
    def start_app(self, app):
        try:
            if not os.path.exists(app['path']):
                print(f"Файл не найден: {app['path']}")
                return False
            
            ext = os.path.splitext(app['path'])[1].lower()
            
            if ext == '.bat' or ext == '.cmd':
                subprocess.Popen(['cmd', '/c', 'start', '', app['path']], shell=True)
            elif ext == '.ps1':
                subprocess.Popen(['powershell', '-ExecutionPolicy', 'Bypass', '-File', app['path']], shell=True)
            else:
                subprocess.Popen([app['path']], shell=True)
            
            app['last_start'] = time.strftime("%H:%M:%S")
            print(f"✅ Запущен: {app['name']}")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска {app['name']}: {e}")
            return False
    
    def is_process_running(self, app):
        """Проверяет, запущен ли отслеживаемый процесс"""
        try:
            import psutil
            track_process = app.get('track_process', os.path.basename(app['path'])).lower()
            
            # Убираем расширение .exe для более гибкого поиска
            if track_process.endswith('.exe'):
                track_process_no_ext = track_process[:-4]
            else:
                track_process_no_ext = track_process
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name']:
                        proc_name = proc.info['name'].lower()
                        # Проверяем точное совпадение или совпадение без расширения
                        if proc_name == track_process or proc_name == track_process_no_ext + '.exe':
                            return True
                except:
                    continue
        except Exception as e:
            print(f"Ошибка проверки процесса: {e}")
        
        return False
    
    def watchdog_loop(self):
        print("🛡️ Сторожевой поток запущен")
        while self.running:
            try:
                for app in self.apps:
                    if not self.is_process_running(app):
                        print(f"⚠️ {app['name']} не запущен (процесс {app.get('track_process')} не найден), перезапускаю...")
                        self.start_app(app)
                        time.sleep(2)
                
                self.root.after(0, self.update_statuses)
                time.sleep(5)
            except Exception as e:
                print(f"Ошибка в сторожевом потоке: {e}")
                time.sleep(5)
    
    def update_statuses(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for app in self.apps:
            try:
                is_running = self.is_process_running(app)
                status = "🟢 Работает" if is_running else "🔴 Не запущено"
            except:
                status = "⚠️ Ошибка"
            
            self.tree.insert("", "end", values=(
                app['name'],
                app['path'],
                app.get('track_process', os.path.basename(app['path'])),
                status,
                app.get('last_start', 'Никогда')
            ))
        
        total = len(self.apps)
        running = sum(1 for app in self.apps if self.is_process_running(app))
        self.status_label.config(text=f"🟢 Статус: Активно слежение | 📊 Всего: {total} | ✅ Работает: {running} | ❌ Остановлено: {total - running}")
    
    def start_watchdog(self):
        if self.watch_thread is None or not self.watch_thread.is_alive():
            self.watch_thread = threading.Thread(target=self.watchdog_loop, daemon=True)
            self.watch_thread.start()
    
    def check_autostart_status(self):
        """Проверяет, включен ли автозапуск"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "Otkyyvashka")
                self.autostart_enabled = True
                self.autostart_var.set(True)
            except:
                self.autostart_enabled = False
                self.autostart_var.set(False)
            key.Close()
        except:
            pass
    
    def toggle_autostart(self):
        """Включает/выключает автозапуск по чекбоксу"""
        try:
            if getattr(sys, 'frozen', False):
                app_path = sys.executable
            else:
                app_path = os.path.abspath(__file__)
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
            
            if self.autostart_var.get():
                winreg.SetValueEx(key, "Otkyyvashka", 0, winreg.REG_SZ, app_path)
                messagebox.showinfo("Автозапуск", "✅ Автозапуск ВКЛЮЧЕН!")
            else:
                try:
                    winreg.DeleteValue(key, "Otkyyvashka")
                    messagebox.showinfo("Автозапуск", "❌ Автозапуск ОТКЛЮЧЕН!")
                except:
                    pass
            
            key.Close()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось изменить автозапуск: {e}")
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.apps, f, ensure_ascii=False, indent=2)
            print(f"💾 Конфиг сохранен: {len(self.apps)} приложений")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.apps = json.load(f)
                print(f"📂 Загружено {len(self.apps)} приложений")
            except:
                self.apps = []
    
    def on_closing(self):
        print("🛑 Закрытие программы...")
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = WatchdogApp(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")