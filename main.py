import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import pylibdmtx.pylibdmtx as dmtx
import numpy as np
import cv2
from tkinter import ttk
import threading
import traceback

class DataMatrixInserter:
    def __init__(self, root):
        self.root = root
        self.root.title("DataMatrix Value Browser")
        self.root.geometry("1400x900")
        
        
        self.image_path = None
        self.original_image = None
        self.preview_image = None
        self.display_image_obj = None
        self.tk_image = None
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.rect_coords = None
        self.canvas_image = None
        self.drawing = False
        self.resizing = False
        self.selected_handle = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        
        
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.zoom_step = 0.1
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.canvas_width = 0
        self.canvas_height = 0
        self.image_width = 0
        self.image_height = 0
        
        
        self.current_dm_image = None
        self.current_dm_array = None
        self.current_data = ""
        self.last_valid_data = ""
        
        
        self.rotation_angle = tk.IntVar(value=0)
        self.transparency = tk.DoubleVar(value=1.0)
        self.selected_data = tk.StringVar()
        
        
        self.correlation_threshold = tk.DoubleVar(value=0.7)
        self.correlation_value = 0.0
        
        
        self.batch_results = []
        self.batch_in_progress = False
        
        
        self.handles = []
        self.handle_size = 8
        
        
        self.update_pending = False
        
        
        self.create_widgets()
        
    def create_widgets(self):
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        
        center_panel = ttk.Frame(main_frame)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        
        right_panel = ttk.Frame(main_frame, width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)
        
        
        
        ttk.Button(left_panel, text="Загрузить изображение", 
                  command=self.load_image).pack(fill=tk.X, pady=5)
        
        
        ttk.Label(left_panel, text="Список значений для перебора:", 
                 font=('Arial', 10, 'bold')).pack(pady=(10,5))
        
        
        self.data_text = scrolledtext.ScrolledText(left_panel, height=6, width=35)
        self.data_text.pack(fill=tk.X, pady=5)
        
        self.data_text.bind('<Control-v>', self.paste_to_data_text)
        self.data_text.bind('<Control-V>', self.paste_to_data_text)
        
        
        list_buttons_frame = ttk.Frame(left_panel)
        list_buttons_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(list_buttons_frame, text="Загрузить из файла", 
                  command=self.load_data_from_file).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        ttk.Button(list_buttons_frame, text="Обновить список", 
                  command=self.update_dropdown_list).pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        
        
        ttk.Label(left_panel, text="Выберите значение из списка:", 
                 font=('Arial', 10)).pack(pady=(10,2), anchor=tk.W)
        
        self.data_combobox = ttk.Combobox(left_panel, textvariable=self.selected_data, 
                                          state='readonly', width=33)
        self.data_combobox.pack(fill=tk.X, pady=2)
        self.data_combobox.bind('<<ComboboxSelected>>', self.on_data_selected)
        
        
        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=10)
        
        
        ttk.Label(left_panel, text="Ручной ввод значения:", 
                 font=('Arial', 10, 'bold')).pack(pady=(0,5))
        
        
        self.input_data = ttk.Entry(left_panel, width=35)
        self.input_data.pack(fill=tk.X, pady=2)
        self.input_data.bind('<KeyRelease>', self.on_data_changed)
        
        self.input_data.bind('<Control-v>', self.paste_to_input)
        self.input_data.bind('<Control-V>', self.paste_to_input)
        
        
        ttk.Button(left_panel, text="Применить ручной ввод", 
                  command=self.apply_manual_value).pack(fill=tk.X, pady=2)
        
        
        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=10)
        
        
        ttk.Label(left_panel, text="Настройки DataMatrix:", 
                 font=('Arial', 10, 'bold')).pack(pady=(0,5))
        
        
        self.area_info = ttk.Label(left_panel, text="Область не выбрана", foreground='gray')
        self.area_info.pack(anchor=tk.W, pady=5)
        
        
        ttk.Label(left_panel, text="Угол поворота (градусы):").pack(anchor=tk.W, pady=(5,2))
        
        rotation_frame = ttk.Frame(left_panel)
        rotation_frame.pack(fill=tk.X, pady=2)
        
        
        self.rotation_scale = ttk.Scale(rotation_frame, from_=0, to=359, 
                                        orient=tk.HORIZONTAL, 
                                        variable=self.rotation_angle,
                                        command=self.on_rotation_changed)
        self.rotation_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        
        self.rotation_entry = ttk.Entry(rotation_frame, textvariable=self.rotation_angle, 
                                        width=5)
        self.rotation_entry.pack(side=tk.RIGHT, padx=(5,0))
        self.rotation_entry.bind('<KeyRelease>', self.on_rotation_changed)
        
        
        rotation_buttons = ttk.Frame(left_panel)
        rotation_buttons.pack(fill=tk.X, pady=2)
        
        ttk.Button(rotation_buttons, text="0°", 
                  command=lambda: self.set_rotation(0)).pack(side=tk.LEFT, padx=2)
        ttk.Button(rotation_buttons, text="90°", 
                  command=lambda: self.set_rotation(90)).pack(side=tk.LEFT, padx=2)
        ttk.Button(rotation_buttons, text="180°", 
                  command=lambda: self.set_rotation(180)).pack(side=tk.LEFT, padx=2)
        ttk.Button(rotation_buttons, text="270°", 
                  command=lambda: self.set_rotation(270)).pack(side=tk.LEFT, padx=2)
        
        
        ttk.Label(left_panel, text="Прозрачность:").pack(anchor=tk.W, pady=(10,2))
        
        transparency_frame = ttk.Frame(left_panel)
        transparency_frame.pack(fill=tk.X, pady=2)
        
        
        self.transparency_scale = ttk.Scale(transparency_frame, from_=0.0, to=1.0, 
                                            orient=tk.HORIZONTAL, 
                                            variable=self.transparency,
                                            command=self.on_transparency_changed)
        self.transparency_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        
        self.transparency_label = ttk.Label(transparency_frame, text="100%", width=5)
        self.transparency_label.pack(side=tk.RIGHT, padx=(5,0))
        
        
        self.transparency.trace('w', self.update_transparency_label)
        
        
        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, pady=10)
        
        
        zoom_frame = ttk.LabelFrame(left_panel, text="Управление масштабом", padding="5")
        zoom_frame.pack(fill=tk.X, pady=5)
        
        
        zoom_buttons = ttk.Frame(zoom_frame)
        zoom_buttons.pack(fill=tk.X, pady=2)
        
        ttk.Button(zoom_buttons, text="+", width=5, 
                  command=self.zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_buttons, text="-", width=5, 
                  command=self.zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_buttons, text="100%", width=8, 
                  command=self.zoom_reset).pack(side=tk.LEFT, padx=2)
        ttk.Button(zoom_buttons, text="Fit", width=5, 
                  command=self.zoom_fit).pack(side=tk.LEFT, padx=2)
        
        
        self.zoom_info = ttk.Label(zoom_frame, text="Масштаб: 100%", foreground='blue')
        self.zoom_info.pack(pady=2)
        
        
        nav_info = ttk.Label(zoom_frame, 
                            text="Средняя кнопка мыши - перемещение\n"
                                 "Ctrl + колесо - масштабирование\n"
                                 "Перетаскивайте угловые маркеры для изменения области", 
                            foreground='gray', justify=tk.LEFT)
        nav_info.pack(pady=2)
        
        
        preview_frame = ttk.LabelFrame(left_panel, text="Предпросмотр", padding="5")
        preview_frame.pack(fill=tk.BOTH, pady=10, expand=True)
        
        
        self.preview_canvas = tk.Canvas(preview_frame, width=200, height=200, bg='white')
        self.preview_canvas.pack()
        
        
        self.info_label = ttk.Label(preview_frame, text="", foreground='blue', wraplength=280)
        self.info_label.pack(pady=5)
        
        
        
        self.canvas = tk.Canvas(center_panel, bg='gray', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        
        
        results_frame = ttk.LabelFrame(right_panel, text="Результаты перебора значений", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        
        self.batch_button = ttk.Button(results_frame, text="Перебрать все значения из списка", 
                                       command=self.start_value_browsing)
        self.batch_button.pack(fill=tk.X, pady=5)
        
        
        self.stop_batch_button = ttk.Button(results_frame, text="Остановить", 
                                           command=self.stop_value_browsing, state=tk.DISABLED)
        self.stop_batch_button.pack(fill=tk.X, pady=2)
        
        
        self.batch_progress = ttk.Progressbar(results_frame, mode='determinate')
        self.batch_progress.pack(fill=tk.X, pady=2)
        
        self.batch_status = ttk.Label(results_frame, text="Готов к перебору", foreground='gray')
        self.batch_status.pack(pady=2)
        
        
        self.debug_info = ttk.Label(results_frame, text="", foreground='blue', wraplength=280)
        self.debug_info.pack(pady=2)
        
        
        results_canvas_frame = ttk.Frame(results_frame)
        results_canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        
        results_scrollbar = ttk.Scrollbar(results_canvas_frame)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        
        self.results_canvas = tk.Canvas(results_canvas_frame, yscrollcommand=results_scrollbar.set,
                                        bg='white', highlightthickness=0)
        self.results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        results_scrollbar.config(command=self.results_canvas.yview)
        
        
        self.results_frame = ttk.Frame(self.results_canvas)
        self.results_canvas.create_window((0, 0), window=self.results_frame, anchor=tk.NW)
        
        
        self.results_frame.bind('<Configure>', self.on_results_frame_configure)
        
        
        self.result_widgets = []
        
        
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.on_pan_move)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom_mousewheel)
        
        
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def on_results_frame_configure(self, event):
        """Обновление области прокрутки при изменении размера фрейма результатов"""
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        
    def paste_to_data_text(self, event):
        """Вставка текста из буфера обмена в поле списка данных"""
        try:
            clipboard_text = self.root.clipboard_get()
            
            self.data_text.insert(tk.INSERT, clipboard_text)
            self.update_dropdown_list()  
            self.status_var.set("Текст вставлен в список значений")
            return "break"  
        except Exception as e:
            self.status_var.set(f"Ошибка вставки: {str(e)}")
            return "break"
            
    def paste_to_input(self, event):
        """Вставка текста из буфера обмена в поле ввода"""
        try:
            clipboard_text = self.root.clipboard_get()
            
            self.input_data.insert(tk.INSERT, clipboard_text)
            self.on_data_changed()  
            self.status_var.set("Текст вставлен в поле ручного ввода")
            return "break"  
        except Exception as e:
            self.status_var.set(f"Ошибка вставки: {str(e)}")
            return "break"
    
    def update_dropdown_list(self):
        """Обновление выпадающего списка из текстового поля"""
        data_text = self.data_text.get('1.0', tk.END).strip()
        if data_text:
            data_list = [d.strip() for d in data_text.split('\n') if d.strip()]
            self.data_combobox['values'] = data_list
            if data_list:
                self.data_combobox.current(0)
                self.selected_data.set(data_list[0])
                self.on_data_selected()
            self.status_var.set(f"Загружено {len(data_list)} значений в список")
            self.debug_info.config(text=f"В списке: {len(data_list)} значений")
        else:
            self.data_combobox['values'] = []
            self.status_var.set("Список пуст")
            self.debug_info.config(text="Список пуст")
    
    def on_data_selected(self, event=None):
        """Обработка выбора данных из выпадающего списка"""
        data = self.selected_data.get()
        if data:
            self.input_data.delete(0, tk.END)
            self.input_data.insert(0, data)
            self.current_data = data
            self.last_valid_data = data
            self.create_current_datamatrix()
            self.update_live_preview()
            self.calculate_correlation()
            self.status_var.set(f"Выбрано значение из списка: {data[:30]}...")
    
    def apply_manual_value(self):
        """Применение значения из ручного ввода"""
        data = self.input_data.get().strip()
        if data:
            self.current_data = data
            self.last_valid_data = data
            self.create_current_datamatrix()
            self.update_live_preview()
            self.calculate_correlation()
            self.status_var.set(f"Применено ручное значение: {data[:30]}...")
        else:
            messagebox.showwarning("Предупреждение", "Введите значение для применения")
    
    def start_value_browsing(self):
        """Запуск перебора всех значений из списка"""
        if self.original_image is None or self.rect_coords is None:
            messagebox.showwarning("Предупреждение", "Не выбрана область на изображении")
            return
            
        
        data_text = self.data_text.get('1.0', tk.END).strip()
        if not data_text:
            messagebox.showwarning("Предупреждение", "Нет данных для перебора")
            return
            
        data_list = [d.strip() for d in data_text.split('\n') if d.strip()]
        if not data_list:
            messagebox.showwarning("Предупреждение", "Нет данных для перебора")
            return
        
        print("=" * 50)
        print(f"Начинаем перебор {len(data_list)} значений")
        print(f"Значения: {data_list}")
        print(f"Размер области: {self.rect_coords}")
        print(f"Угол поворота: {self.rotation_angle.get()}")
        print("=" * 50)
        
        
        self.clear_results_widgets()
        
        
        self.batch_in_progress = True
        self.batch_button.config(state=tk.DISABLED)
        self.stop_batch_button.config(state=tk.NORMAL)
        self.batch_status.config(text="Перебор значений...", foreground='blue')
        self.batch_progress['value'] = 0
        self.debug_info.config(text=f"Обрабатывается {len(data_list)} значений...")
        
        thread = threading.Thread(target=self.value_browsing_thread, args=(data_list,))
        thread.daemon = True
        thread.start()
        
    def stop_value_browsing(self):
        """Остановка перебора значений"""
        self.batch_in_progress = False
        self.batch_status.config(text="Остановлено пользователем", foreground='red')
        self.batch_button.config(state=tk.NORMAL)
        self.stop_batch_button.config(state=tk.DISABLED)
        self.debug_info.config(text="Перебор остановлен")
        
    def value_browsing_thread(self, data_list):
        """Поток для перебора значений"""
        try:
            x1, y1, x2, y2 = self.rect_coords
            size = min(x2 - x1, y2 - y1)  
            roi = self.original_image[y1:y1+size, x1:x1+size]
            
            print(f"Размер области: {size}x{size}")
            print(f"Форма ROI: {roi.shape}")
            
            
            if len(roi.shape) == 3:
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
                print("ROI конвертирован в оттенки серого")
            else:
                roi_gray = roi
                
            roi_binary = self.discretize_image(roi_gray)
            print(f"ROI бинаризирован, форма: {roi_binary.shape}")
            
            total = len(data_list)
            results = []
            
            for i, data in enumerate(data_list):
                if not self.batch_in_progress:
                    print("Перебор остановлен пользователем")
                    break
                
                print(f"\n--- Обработка {i+1}/{total} ---")
                print(f"Данные: {data}")
                    
                
                dm_image = self.create_datamatrix_binary(data, size, self.rotation_angle.get())
                
                if dm_image:
                    print(f"DataMatrix создан успешно, размер: {dm_image.size}")
                    
                    
                    dm_binary = np.array(dm_image.convert('L'))
                    print(f"DM массив форма: {dm_binary.shape}")
                    
                    dm_binary = self.discretize_image(dm_binary)
                    
                    
                    correlation = self.normalized_correlation(roi_binary, dm_binary)
                    print(f"Корреляция: {correlation:.4f}")
                    
                    
                    result = {
                        'data': data,
                        'correlation': correlation,
                        'preview': self.create_datamatrix(data, 64)  
                    }
                    results.append(result)
                else:
                    print(f"ОШИБКА: Не удалось создать DataMatrix для {data}")
                
                
                progress = int((i + 1) / total * 100)
                self.root.after(0, self.update_batch_progress, progress, i + 1, total)
            
            print(f"\n=== ИТОГИ ===")
            print(f"Получено результатов: {len(results)} из {total}")
            if results:
                print("Первые 3 результата:")
                for j, r in enumerate(results[:3]):
                    print(f"  {j+1}. {r['data'][:20]}... - {r['correlation']:.4f}")
            
            
            results.sort(key=lambda x: x['correlation'], reverse=True)
            self.batch_results = results
            
            
            self.root.after(0, self.display_batch_results)
            
        except Exception as e:
            print(f"!!! ОШИБКА В ПОТОКЕ: {str(e)}")
            traceback.print_exc()
            self.root.after(0, messagebox.showerror, "Ошибка", f"Ошибка при переборе: {str(e)}")
        finally:
            self.batch_in_progress = False
            self.root.after(0, self.value_browsing_finished)
            
    def update_batch_progress(self, progress, current, total):
        """Обновление прогресса перебора"""
        self.batch_progress['value'] = progress
        self.batch_status.config(text=f"Обработано: {current}/{total}")
        self.debug_info.config(text=f"Обработано {current}/{total}, найдено {len(self.batch_results)} результатов")
        
    def value_browsing_finished(self):
        """Завершение перебора значений"""
        self.batch_button.config(state=tk.NORMAL)
        self.stop_batch_button.config(state=tk.DISABLED)
        if self.batch_results:
            self.batch_status.config(text=f"Перебор завершен: {len(self.batch_results)} результатов", 
                                    foreground='green')
            self.debug_info.config(text=f"Найдено {len(self.batch_results)} результатов")
        else:
            self.batch_status.config(text="Перебор завершен (нет результатов)", foreground='orange')
            self.debug_info.config(text="Нет результатов. Проверьте консоль для отладки")
        self.batch_in_progress = False
        
    def clear_results_widgets(self):
        """Очистка только виджетов результатов, но не данных"""
        print(f"Очистка виджетов результатов. Было виджетов: {len(self.result_widgets)}")
        for widget in self.result_widgets:
            try:
                widget.destroy()
            except:
                pass
        self.result_widgets.clear()
        print(f"После очистки виджетов: {len(self.result_widgets)}")
        
        
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
    def display_batch_results(self):
        """Отображение результатов перебора"""
        print(f"\n=== ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ===")
        print(f"Количество результатов в self.batch_results: {len(self.batch_results)}")
        
        
        self.clear_results_widgets()
        
        if len(self.batch_results) == 0:
            print("НЕТ РЕЗУЛЬТАТОВ для отображения")
            
            no_results_label = ttk.Label(self.results_frame, 
                                        text="Нет результатов.\nПроверьте консоль для отладки", 
                                        foreground='gray', justify=tk.CENTER)
            no_results_label.pack(pady=20)
            self.result_widgets.append(no_results_label)
            return
        
        print(f"Отображение {len(self.batch_results)} результатов в интерфейсе")
        
        for i, result in enumerate(self.batch_results):
            print(f"Создание элемента {i+1} для: {result['data'][:20]}...")
            
            
            item_frame = ttk.Frame(self.results_frame, relief=tk.RIDGE, borderwidth=1)
            item_frame.pack(fill=tk.X, padx=2, pady=2)
            
            
            item_frame.bind('<Button-1>', lambda e, idx=i: self.on_result_selected(idx))
            
            
            preview = result['preview']
            if preview:
                try:
                    preview_tk = ImageTk.PhotoImage(preview)
                    preview_label = ttk.Label(item_frame, image=preview_tk)
                    preview_label.image = preview_tk  
                    preview_label.pack(side=tk.LEFT, padx=5, pady=5)
                    preview_label.bind('<Button-1>', lambda e, idx=i: self.on_result_selected(idx))
                    print(f"  Миниатюра создана")
                except Exception as e:
                    print(f"  Ошибка создания миниатюры: {e}")
            else:
                print(f"  Нет preview для результата")
            
            
            info_frame = ttk.Frame(item_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            info_frame.bind('<Button-1>', lambda e, idx=i: self.on_result_selected(idx))
            
            
            data_text = result['data']
            if len(data_text) > 25:
                display_data = data_text[:22] + '...'
            else:
                display_data = data_text
                
            data_label = ttk.Label(info_frame, text=f"Значение: {display_data}", 
                                  font=('Arial', 8, 'bold'), wraplength=150)
            data_label.pack(anchor=tk.W)
            data_label.bind('<Button-1>', lambda e, idx=i: self.on_result_selected(idx))
            
            
            percent = int(result['correlation'] * 100)
            color = 'green' if result['correlation'] >= self.correlation_threshold.get() else 'red'
            corr_label = ttk.Label(info_frame, text=f"Похожесть: {percent}%", 
                                  foreground=color, font=('Arial', 8, 'bold'))
            corr_label.pack(anchor=tk.W)
            corr_label.bind('<Button-1>', lambda e, idx=i: self.on_result_selected(idx))
            
            self.result_widgets.append(item_frame)
            print(f"  Элемент {i+1} добавлен в список виджетов")
        
        print(f"Всего виджетов в списке: {len(self.result_widgets)}")
        
        
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        self.batch_status.config(text=f"Найдено {len(self.batch_results)} результатов", foreground='green')
        self.debug_info.config(text=f"Отображено {len(self.batch_results)} результатов")
        
        
        self.results_frame.update_idletasks()
        self.results_canvas.update_idletasks()
        print("=== ОТОБРАЖЕНИЕ ЗАВЕРШЕНО ===\n")
        
    def on_result_selected(self, index):
        """Обработка выбора результата из списка"""
        if index < 0 or index >= len(self.batch_results):
            return
            
        
        for i, widget in enumerate(self.result_widgets):
            if i == index:
                widget.config(style='Selected.TFrame')
            else:
                widget.config(style='TFrame')
        
        
        style = ttk.Style()
        style.configure('Selected.TFrame', background='lightblue')
        
        result = self.batch_results[index]
        
        
        self.input_data.delete(0, tk.END)
        self.input_data.insert(0, result['data'])
        
        
        self.current_data = result['data']
        self.create_current_datamatrix()
        self.update_live_preview()
        
        
        self.correlation_value = result['correlation']
        self.update_correlation_display()
        
        self.status_var.set(f"Выбрано значение: {result['data'][:30]}... (похожесть {int(result['correlation']*100)}%)")
    
    def calculate_correlation(self):
        """Расчет корреляции между выделенной областью и текущим DataMatrix"""
        if self.original_image is None or self.rect_coords is None:
            return 0.0
            
        if not self.current_data:
            return 0.0
            
        x1, y1, x2, y2 = self.rect_coords
        size = min(x2 - x1, y2 - y1)  
        
        if size <= 0:
            return 0.0
            
        
        roi = self.original_image[y1:y1+size, x1:x1+size]
        
        
        dm_image = self.create_datamatrix_binary(self.current_data, size, self.rotation_angle.get())
        
        if dm_image is None:
            return 0.0
            
        
        if len(roi.shape) == 3:
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        else:
            roi_gray = roi
            
        
        roi_binary = self.discretize_image(roi_gray)
        dm_binary = self.discretize_image(np.array(dm_image.convert('L')))
        
        
        correlation = self.normalized_correlation(roi_binary, dm_binary)
        
        self.correlation_value = correlation
        self.update_correlation_display()
        
        return correlation
    
    def discretize_image(self, image, threshold=128):
        """Дискретизация изображения (бинаризация)"""
        _, binary = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
        return binary
    
    def normalized_correlation(self, img1, img2):
        """Вычисление нормализованной корреляции между двумя изображениями"""
        
        if img1.shape != img2.shape:
            
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
        img1_norm = img1.astype(np.float32) / 255.0
        img2_norm = img2.astype(np.float32) / 255.0
        
        mean1 = np.mean(img1_norm)
        mean2 = np.mean(img2_norm)
        
        numerator = np.sum((img1_norm - mean1) * (img2_norm - mean2))
        denominator = np.sqrt(np.sum((img1_norm - mean1)**2) * np.sum((img2_norm - mean2)**2))
        
        if denominator == 0:
            return 0
            
        correlation = numerator / denominator
        
        correlation = (correlation + 1) / 2
        return max(0, min(1, correlation))
    
    def create_datamatrix_binary(self, data, size, angle=0):
        """Создание бинарного DataMatrix кода для корреляции"""
        try:
            if not data:
                return None
                
            print(f"  Создание DataMatrix для: {data[:20]}... размер {size}")
                
            encoded = dmtx.encode(data.encode('utf-8'))
            
            if hasattr(encoded, 'pixels'):
                img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
                print(f"  Исходный размер DataMatrix: {encoded.width}x{encoded.height}")
            else:
                img = encoded[0]
                print(f"  Исходный размер DataMatrix: {img.size}")
            
            img = img.convert('L')
            
            img_array = np.array(img)
            binary_array = np.where(img_array < 128, 0, 255).astype(np.uint8)
            img = Image.fromarray(binary_array, 'L')
            
            img = img.resize((size, size), Image.Resampling.NEAREST)
            
            if angle != 0:
                img = img.rotate(angle, expand=True, 
                                 resample=Image.Resampling.NEAREST, 
                                 fillcolor=255)
                
                if img.size != (size, size):
                    new_img = Image.new('L', (size, size), 255)
                    offset_x = (size - img.size[0]) // 2
                    offset_y = (size - img.size[1]) // 2
                    new_img.paste(img, (offset_x, offset_y))
                    img = new_img
            
            return img
        except Exception as e:
            print(f"  !!! Ошибка создания бинарного DataMatrix: {e}")
            traceback.print_exc()
            return None
    
    def update_correlation_display(self):
        """Обновление отображения информации о корреляции"""
        percent = int(self.correlation_value * 100)
        
        
        threshold = self.correlation_threshold.get()
        
        if self.correlation_value >= threshold:
            status_text = f"Похожесть: {percent}% ✓"
        else:
            status_text = f"Похожесть: {percent}% ✗"
            
        
        if self.current_data:
            self.status_var.set(f"Текущее: {self.current_data[:30]}... {status_text}")
        else:
            self.status_var.set(status_text)
        
    def set_rotation(self, angle):
        """Установка угла поворота"""
        self.rotation_angle.set(angle)
        self.on_rotation_changed()
        
    def update_transparency_label(self, *args):
        """Обновление метки прозрачности"""
        percent = int(self.transparency.get() * 100)
        self.transparency_label.config(text=f"{percent}%")
        
    def on_data_changed(self, event=None):
        """Обработка изменения данных в поле ввода"""
        data = self.input_data.get().strip()
        if data:
            self.current_data = data
            self.last_valid_data = data
            self.create_current_datamatrix()
            self.update_live_preview()
            self.calculate_correlation()
    
    def on_rotation_changed(self, event=None):
        """Обработка изменения угла поворота"""
        self.update_live_preview()
        if self.current_data:
            self.calculate_correlation()
    
    def on_transparency_changed(self, event=None):
        """Обработка изменения прозрачности"""
        self.update_live_preview()
    
    
    def zoom_in(self):
        self.zoom_level = min(self.max_zoom, self.zoom_level + self.zoom_step)
        self.update_zoom_display()
        
    def zoom_out(self):
        self.zoom_level = max(self.min_zoom, self.zoom_level - self.zoom_step)
        self.update_zoom_display()
        
    def zoom_reset(self):
        self.zoom_level = 1.0
        self.update_zoom_display()
        
    def zoom_fit(self):
        if self.preview_image is not None:
            height, width = self.preview_image.shape[:2]
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 0 and canvas_height > 0:
                zoom_x = canvas_width / width
                zoom_y = canvas_height / height
                self.zoom_level = min(zoom_x, zoom_y)
                self.update_zoom_display()
    
    def on_pan_start(self, event):
        self.pan_start_x = self.canvas.canvasx(event.x)
        self.pan_start_y = self.canvas.canvasy(event.y)
        self.canvas.scan_mark(event.x, event.y)
        
    def on_pan_move(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        
    def on_mousewheel(self, event):
        if event.state & 0x0004:
            self.on_zoom_mousewheel(event)
        else:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def on_zoom_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def update_zoom_display(self):
        self.refresh_display()
        self.zoom_info.config(text=f"Масштаб: {int(self.zoom_level * 100)}%")
        
    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if file_path:
            self.image_path = file_path
            pil_image = Image.open(file_path)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            self.original_image = np.array(pil_image)
            self.preview_image = self.original_image.copy()
            
            self.zoom_level = 1.0
            self.zoom_info.config(text="Масштаб: 100%")
            
            self.refresh_display()
            self.status_var.set(f"Загружено: {file_path}")
    
    def refresh_display(self):
        if self.preview_image is not None:
            height, width = self.preview_image.shape[:2]
            
            new_width = int(width * self.zoom_level)
            new_height = int(height * self.zoom_level)
            
            self.image_width = width
            self.image_height = height
            
            self.scale_x = width / new_width
            self.scale_y = height / new_height
            
            resized = cv2.resize(self.preview_image, (new_width, new_height))
            self.display_image_obj = Image.fromarray(resized)
            self.tk_image = ImageTk.PhotoImage(self.display_image_obj)
            
            self.canvas.delete("all")
            self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
            self.canvas.config(scrollregion=(0, 0, new_width, new_height))
            
            self.canvas_width = new_width
            self.canvas_height = new_height
            
            if self.rect_coords:
                self.draw_rectangle_and_handles()
    
    def draw_rectangle_and_handles(self):
        """Отрисовка прямоугольника и двух угловых ручек"""
        if not self.rect_coords:
            return
            
        x1, y1, x2, y2 = self.rect_coords
        
        
        canvas_x1 = x1 / self.scale_x
        canvas_y1 = y1 / self.scale_y
        canvas_x2 = x2 / self.scale_x
        canvas_y2 = y2 / self.scale_y
        
        
        if self.rect:
            self.canvas.delete(self.rect)
        for handle in self.handles:
            self.canvas.delete(handle)
        self.handles.clear()
        
        
        self.rect = self.canvas.create_rectangle(
            canvas_x1, canvas_y1, canvas_x2, canvas_y2,
            outline='red', width=2, dash=(5, 3)
        )
        
        
        handle_positions = [
            ('nw', canvas_x1, canvas_y1),  
            ('se', canvas_x2, canvas_y2),  
        ]
        
        for handle_id, x, y in handle_positions:
            handle = self.canvas.create_rectangle(
                x - self.handle_size/2, y - self.handle_size/2,
                x + self.handle_size/2, y + self.handle_size/2,
                fill='white', outline='red', width=2,
                tags=(handle_id,)
            )
            self.handles.append(handle)
    
    def get_handle_at_position(self, x, y):
        """Определяет, находится ли позиция на ручке изменения размера"""
        if not self.rect_coords:
            return None
            
        x1, y1, x2, y2 = self.rect_coords
        canvas_x1 = x1 / self.scale_x
        canvas_y1 = y1 / self.scale_y
        canvas_x2 = x2 / self.scale_x
        canvas_y2 = y2 / self.scale_y
        
        
        handle_positions = [
            ('nw', canvas_x1, canvas_y1),  
            ('se', canvas_x2, canvas_y2),  
        ]
        
        for handle_id, hx, hy in handle_positions:
            if (hx - self.handle_size <= x <= hx + self.handle_size and
                hy - self.handle_size <= y <= hy + self.handle_size):
                return handle_id
        return None
    
    def on_mouse_down(self, event):
        if self.display_image_obj:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            
            handle = self.get_handle_at_position(x, y)
            if handle:
                self.resizing = True
                self.selected_handle = handle
                self.start_x = x
                self.start_y = y
                self.original_rect = self.rect_coords
                print(f"Начало изменения размера за ручку: {handle}")
            else:
                self.drawing = True
                self.start_x = x
                self.start_y = y
                if self.rect:
                    self.canvas.delete(self.rect)
                for handle in self.handles:
                    self.canvas.delete(handle)
                self.handles.clear()
                self.rect = self.canvas.create_rectangle(
                    self.start_x, self.start_y, self.start_x, self.start_y,
                    outline='red', width=2, dash=(5, 3)
                )
    
    def on_mouse_move(self, event):
        if self.drawing:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)
            
        elif self.resizing and self.selected_handle and self.original_rect:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            
            
            x1, y1, x2, y2 = self.original_rect
            
            
            canvas_x1 = x1 / self.scale_x
            canvas_y1 = y1 / self.scale_y
            canvas_x2 = x2 / self.scale_x
            canvas_y2 = y2 / self.scale_y
            
            
            if self.selected_handle == 'nw':
                
                new_x1 = cur_x
                new_y1 = cur_y
                new_x2 = canvas_x2
                new_y2 = canvas_y2
                
            elif self.selected_handle == 'se':
                
                new_x1 = canvas_x1
                new_y1 = canvas_y1
                new_x2 = cur_x
                new_y2 = cur_y
                
            else:
                return
            
            
            self.canvas.coords(self.rect, new_x1, new_y1, new_x2, new_y2)
            
            
            for handle in self.handles:
                self.canvas.delete(handle)
            self.handles.clear()
            
            
            handle_positions = [
                ('nw', new_x1, new_y1),
                ('se', new_x2, new_y2),
            ]
            
            for handle_id, hx, hy in handle_positions:
                handle = self.canvas.create_rectangle(
                    hx - self.handle_size/2, hy - self.handle_size/2,
                    hx + self.handle_size/2, hy + self.handle_size/2,
                    fill='white', outline='red', width=2
                )
                self.handles.append(handle)
    
    def on_mouse_up(self, event):
        if self.drawing:
            self.drawing = False
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)
            
            if self.display_image_obj:
                x1 = int(min(self.start_x, end_x) * self.scale_x)
                y1 = int(min(self.start_y, end_y) * self.scale_y)
                x2 = int(max(self.start_x, end_x) * self.scale_x)
                y2 = int(max(self.start_y, end_y) * self.scale_y)
                
                
                x1 = max(0, min(x1, self.image_width))
                y1 = max(0, min(y1, self.image_height))
                x2 = max(0, min(x2, self.image_width))
                y2 = max(0, min(y2, self.image_height))
                
                
                self.rect_coords = (x1, y1, x2, y2)
                width = x2 - x1
                height = y2 - y1
                self.area_info.config(text=f"Область: {width}x{height} пикс.")
                self.status_var.set(f"Выбрана область: {width}x{height} пикселей")
                
                self.draw_rectangle_and_handles()
                if self.current_data:
                    self.update_live_preview()
                    self.calculate_correlation()
                
        elif self.resizing:
            self.resizing = False
            
            if self.rect_coords and self.display_image_obj:
                
                canvas_coords = self.canvas.coords(self.rect)
                if canvas_coords:
                    canvas_x1, canvas_y1, canvas_x2, canvas_y2 = canvas_coords
                    
                    
                    x1 = int(canvas_x1 * self.scale_x)
                    y1 = int(canvas_y1 * self.scale_y)
                    x2 = int(canvas_x2 * self.scale_x)
                    y2 = int(canvas_y2 * self.scale_y)
                    
                    
                    x1 = max(0, min(x1, self.image_width))
                    y1 = max(0, min(y1, self.image_height))
                    x2 = max(0, min(x2, self.image_width))
                    y2 = max(0, min(y2, self.image_height))
                    
                    
                    self.rect_coords = (x1, y1, x2, y2)
                    width = x2 - x1
                    height = y2 - y1
                    self.area_info.config(text=f"Область: {width}x{height} пикс.")
                    
                    self.draw_rectangle_and_handles()
                    if self.current_data:
                        self.update_live_preview()
                        self.calculate_correlation()
                        
            self.selected_handle = None
            self.original_rect = None
    
    def load_data_from_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                    self.data_text.delete('1.0', tk.END)
                    self.data_text.insert('1.0', data)
                self.update_dropdown_list()
                self.status_var.set(f"Данные загружены из: {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {str(e)}")
    
    def create_datamatrix(self, data, size):
        """Создание DataMatrix кода с поворотом и прозрачностью"""
        try:
            if not data:
                return None
                
            encoded = dmtx.encode(data.encode('utf-8'))
            
            if hasattr(encoded, 'pixels'):
                img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
            else:
                img = encoded[0]
            
            img = img.convert('RGBA')
            
            pixels = np.array(img)
            
            is_black = np.all(pixels[:, :, :3] < [50, 50, 50], axis=2)
            
            new_pixels = np.zeros((pixels.shape[0], pixels.shape[1], 4), dtype=np.uint8)
            
            new_pixels[is_black, :3] = [0, 0, 0]
            new_pixels[is_black, 3] = int(255 * self.transparency.get())
            
            new_pixels[~is_black, 3] = 0
            
            img = Image.fromarray(new_pixels, 'RGBA')
            
            
            img = img.resize((size, size), Image.Resampling.NEAREST)
            
            if self.rotation_angle.get() != 0:
                img = img.rotate(self.rotation_angle.get(), expand=True, 
                                 resample=Image.Resampling.NEAREST)
                
                if img.size != (size, size):
                    new_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                    offset_x = (size - img.size[0]) // 2
                    offset_y = (size - img.size[1]) // 2
                    new_img.paste(img, (offset_x, offset_y), img)
                    img = new_img
            
            return img
        except Exception as e:
            print(f"Ошибка создания DataMatrix: {e}")
            return None
    
    def create_current_datamatrix(self):
        """Создание текущего DataMatrix для предпросмотра"""
        data = self.input_data.get().strip()
        if data:
            self.current_dm_image = self.create_datamatrix(data, 180)
            if self.current_dm_image:
                dm_tk = ImageTk.PhotoImage(self.current_dm_image)
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(100, 100, image=dm_tk)
                self.preview_canvas.image = dm_tk
                
                self.info_label.config(
                    text=f"Угол: {self.rotation_angle.get()}° | "
                         f"Прозрачность: {int(self.transparency.get()*100)}%"
                )
    
    def update_live_preview(self):
        """Обновление предпросмотра с наложением на изображение"""
        if self.original_image is None or self.rect_coords is None:
            return
            
        if not self.current_data:
            return
            
        x1, y1, x2, y2 = self.rect_coords
        width = x2 - x1
        height = y2 - y1
        size = min(width, height)  
        
        if size <= 0:
            return
            
        self.preview_image = self.original_image.copy()
        
        
        dm_image = self.create_datamatrix(self.current_data, size)
        
        if dm_image:
            if self.preview_image.shape[2] == 3:
                preview_rgba = np.dstack([self.preview_image, 
                                         np.full((self.preview_image.shape[0], 
                                                 self.preview_image.shape[1]), 255, dtype=np.uint8)])
            else:
                preview_rgba = self.preview_image
            
            dm_array = np.array(dm_image)
            
            
            x_offset = x1 + (width - size) // 2
            y_offset = y1 + (height - size) // 2
            
            
            for c in range(3):
                alpha = dm_array[:, :, 3] / 255.0
                preview_rgba[y_offset:y_offset+size, x_offset:x_offset+size, c] = \
                    (preview_rgba[y_offset:y_offset+size, x_offset:x_offset+size, c] * (1 - alpha) + 
                     dm_array[:, :, c] * alpha).astype(np.uint8)
            
            self.preview_image = preview_rgba[:, :, :3]
            
            self.refresh_display()
            self.status_var.set(f"Предпросмотр обновлен: угол {self.rotation_angle.get()}°, "
                               f"прозрачность {int(self.transparency.get()*100)}%")

def main():
    root = tk.Tk()
    app = DataMatrixInserter(root)
    root.mainloop()

if __name__ == "__main__":
    main()