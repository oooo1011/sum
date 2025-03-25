import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time
from typing import List, Dict
from collections import Counter
import queue

class NumberCombinationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("数字组合计算器 (异步版)")
        
        # 初始化变量
        self.numbers = []
        self.target = tk.DoubleVar(value=100.0)
        self.find_all = tk.BooleanVar(value=False)
        self.use_parallel = tk.BooleanVar(value=True)
        self.chunk_size = tk.IntVar(value=1000)
        
        # 用于异步通信
        self.result_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.calculation_running = False
        
        # 创建界面
        self.create_widgets()
        
        # 启动进度更新检查
        self.check_progress()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 目标值输入
        input_frame = ttk.LabelFrame(main_frame, text="输入设置", padding="5")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(input_frame, text="目标值:").grid(row=0, column=0, padx=5, pady=5)
        ttk.Entry(input_frame, textvariable=self.target, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        # 选项框架
        options_frame = ttk.LabelFrame(main_frame, text="计算选项", padding="5")
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Checkbutton(options_frame, text="查找所有组合", variable=self.find_all).grid(row=0, column=0, padx=5)
        ttk.Checkbutton(options_frame, text="启用并行计算", variable=self.use_parallel).grid(row=0, column=1, padx=5)
        
        # 按钮框架
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.import_btn = ttk.Button(buttons_frame, text="导入数字", command=self.import_numbers)
        self.import_btn.grid(row=0, column=0, padx=5)
        
        self.calc_btn = ttk.Button(buttons_frame, text="计算组合", command=self.start_calculation)
        self.calc_btn.grid(row=0, column=1, padx=5)
        
        self.stop_btn = ttk.Button(buttons_frame, text="停止计算", command=self.stop_calculation, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=2, padx=5)
        
        # 进度框架
        progress_frame = ttk.LabelFrame(main_frame, text="计算进度", padding="5")
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, length=300, mode='determinate', 
                                          variable=self.progress_var)
        self.progress_bar.grid(row=0, column=0, columnspan=2, pady=5, padx=5)
        
        self.status_label = ttk.Label(progress_frame, text="就绪")
        self.status_label.grid(row=1, column=0, columnspan=2, pady=2)
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="计算结果", padding="5")
        result_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.result_text = tk.Text(result_frame, height=15, width=60)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text['yscrollcommand'] = scrollbar.set

    def check_progress(self):
        """定期检查进度队列和结果队列"""
        try:
            while True:
                # 检查进度更新
                try:
                    progress, status = self.progress_queue.get_nowait()
                    self.progress_var.set(progress)
                    self.status_label.config(text=status)
                except queue.Empty:
                    pass

                # 检查结果
                try:
                    result = self.result_queue.get_nowait()
                    self.handle_calculation_complete(result)
                except queue.Empty:
                    pass

                break
        finally:
            # 如果还在计算，继续检查
            if self.calculation_running:
                self.root.after(100, self.check_progress)
            else:
                self.progress_var.set(0)
                self.status_label.config(text="就绪")
                self.calc_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)

    def import_numbers(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    raw_numbers = [float(num) for num in content.split() if num.replace('.', '').isdigit()]
                    self.numbers = [round(num, 2) for num in raw_numbers]
                    
                    # 显示数字统计信息
                    number_counts = Counter(self.numbers)
                    stats = "\n".join(f"数字 {num}: {count} 个" 
                                    for num, count in sorted(number_counts.items()))
                    self.result_text.delete(1.0, tk.END)
                    self.result_text.insert(tk.END, f"已导入数字统计:\n{stats}\n")
                    
                messagebox.showinfo("成功", f"已导入 {len(self.numbers)} 个数字")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {str(e)}")

    def start_calculation(self):
        if not self.numbers:
            messagebox.showwarning("警告", "请先导入数字列表")
            return
            
        self.calculation_running = True
        self.calc_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"开始查找组合(目标值: {self.target.get()})...\n")
        
        # 在新线程中启动计算
        threading.Thread(target=self.run_calculation, daemon=True).start()
        # 启动进度检查
        self.check_progress()

    def stop_calculation(self):
        self.calculation_running = False
        self.progress_queue.put((0, "计算已停止"))
        self.calc_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def run_calculation(self):
        """在后台线程中运行计算"""
        try:
            target = self.target.get()
            start_time = time.time()
            
            # 基本检查
            if sum(self.numbers) < target:
                self.result_queue.put(("未找到符合条件的组合\n所有数字之和小于目标值", []))
                return
            
            if min(self.numbers) > target:
                self.result_queue.put(("未找到符合条件的组合\n所有数字都大于目标值", []))
                return
            
            results = self.calculate_combinations(target)
            end_time = time.time()
            
            # 发送结果
            self.result_queue.put((f"计算完成，用时: {end_time - start_time:.2f} 秒", results))
            
        except Exception as e:
            self.result_queue.put((f"计算错误: {str(e)}", []))
        finally:
            self.calculation_running = False

    def calculate_combinations(self, target: float) -> List[List[float]]:
        """计算组合的核心逻辑"""
        target_int = int(target * 100)
        dp = {0: [[]]}
        total_iterations = len(self.numbers)
        
        for i, num in enumerate(self.numbers):
            if not self.calculation_running:
                return []
                
            num_int = int(round(num * 100))
            new_sums = {}
            
            for curr_sum, combinations in list(dp.items()):
                if curr_sum + num_int <= target_int:
                    new_combinations = [combo + [num] for combo in combinations]
                    if curr_sum + num_int in new_sums:
                        new_sums[curr_sum + num_int].extend(new_combinations)
                    else:
                        new_sums[curr_sum + num_int] = new_combinations
                    
                    if not self.find_all.get() and curr_sum + num_int == target_int:
                        return new_combinations[:1]
            
            dp.update(new_sums)
            
            # 更新进度
            progress = (i + 1) * 100 / total_iterations
            self.progress_queue.put((progress, f"计算中... {progress:.1f}%"))
            
            # 定期清理内存
            if i % 10 == 0 and not self.find_all.get():
                dp = {k: v for k, v in dp.items() if k + min(self.numbers) * 100 <= target_int}
        
        return dp.get(target_int, [])

    def handle_calculation_complete(self, result):
        """处理计算结果"""
        message, combinations = result
        self.result_text.delete(1.0, tk.END)
        
        if not combinations:
            self.result_text.insert(tk.END, message)
        else:
            self.result_text.insert(tk.END, f"找到 {len(combinations)} 个组合:\n\n")
            for i, combo in enumerate(combinations, 1):
                self.result_text.insert(tk.END, 
                    f"组合 {i}: {[round(x, 2) for x in combo]} (总和: {sum(combo):.2f})\n")
            self.result_text.insert(tk.END, f"\n{message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = NumberCombinationApp(root)
    root.mainloop()