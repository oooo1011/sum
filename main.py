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
        self.progress_queue.put((0, "正在停止计算..."))
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
        if not self.use_parallel.get():
            return self._calculate_combinations_sequential(target)
            
        from multiprocessing import Pool, cpu_count, Manager
        import math
        
        target_int = int(target * 100)
        num_workers = cpu_count() * 2  # 使用双倍CPU核心数
        chunk_size = max(50, len(self.numbers) // (num_workers * 2))  # 更小的块大小
        
        # 将数字列表分块
        chunks = [self.numbers[i:i+chunk_size] 
                 for i in range(0, len(self.numbers), chunk_size)]
        
        # 使用Manager共享状态
        with Manager() as manager:
            # 创建共享字典和事件
            shared_dict = manager.dict()
            shared_dict[0] = [[]]
            stop_event = manager.Event()
            progress_value = manager.Value('d', 0.0)
            status_text = manager.Value('c', "并行计算中...".encode())
            
            # 使用进程池并行计算
            with Pool(processes=num_workers) as pool:
                try:
                    results = []
                    total_processed = 0
                    processed_chunks = 0
                    
                    # 提交所有任务
                    for chunk in chunks:
                        if not self.calculation_running:
                            break
                        result = pool.apply_async(
                            worker,
                            (chunk, target_int, self.find_all.get(), shared_dict, stop_event)
                        )
                        results.append(result)
                    
                    # 监控进度
                    total_numbers = len(self.numbers)
                    processed_numbers = 0
                    last_update_time = time.time()
                    
                    while self.calculation_running and processed_chunks < len(results):
                        time.sleep(0.1)  # 减少CPU占用
                        
                        # 检查已完成的任务
                        ready = []
                        for r in results:
                            if r.ready():
                                ready.append(r)
                                try:
                                    chunk_result = r.get(timeout=0.1)
                                    if chunk_result:
                                        processed_numbers += len(chunk_result)
                                except:
                                    pass
                        
                        processed_chunks = len(ready)
                        
                        # 更平滑的进度计算
                        # 块处理基础进度(20%) + 数字处理进度(80%)
                        base_progress = processed_chunks / len(chunks) * 20
                        number_progress = processed_numbers / total_numbers * 80
                        progress = min(99, base_progress + number_progress)
                        
                        # 更频繁的进度更新(每秒最多20次)
                        if time.time() - last_update_time > 0.05:
                            # 添加进度平滑 - 每次更新不超过5%
                            if progress - progress_value.value > 5:
                                progress_value.value += 5
                            else:
                                progress_value.value = progress
                                
                            status_text.value = f"并行计算中... {progress_value.value:.1f}%".encode()
                            self.progress_queue.put((progress_value.value, status_text.value.decode()))
                            last_update_time = time.time()
                        
                        # 检查停止信号
                        if not self.calculation_running:
                            stop_event.set()
                            pool.terminate()  # 立即终止所有进程
                            break
                    
                    # 合并结果
                    final_result = []
                    for result in results:
                        if not self.calculation_running:
                            break
                            
                        try:
                            chunk_dp = result.get(timeout=0.1)
                            if chunk_dp and target_int in chunk_dp:
                                final_result.extend(chunk_dp[target_int])
                                if not self.find_all.get():
                                    return final_result[:1]
                        except:
                            continue
                    
                    # 最终进度更新
                    if self.calculation_running:
                        progress_value.value = 100
                        status_text.value = "正在合并结果...".encode()
                        self.progress_queue.put((progress_value.value, status_text.value.decode()))
                
                finally:
                    # 确保资源释放
                    stop_event.set()
                    pool.terminate()
                    pool.join()
            return final_result

    def _calculate_chunk_combinations(self, numbers_chunk, target_int, find_all):
        """计算单个块的组合"""
        dp = {0: [[]]}
        min_num = min(numbers_chunk) * 100 if numbers_chunk else 0
        
        for i, num in enumerate(numbers_chunk):
            num_int = int(round(num * 100))
            new_sums = {}
            
            for curr_sum, combinations in list(dp.items()):
                if curr_sum + num_int <= target_int:
                    # 限制组合数量，最多存储100个组合
                    new_combinations = [combo + [num] for combo in combinations][:100]
                    if curr_sum + num_int in new_sums:
                        new_sums[curr_sum + num_int].extend(new_combinations)
                    else:
                        new_sums[curr_sum + num_int] = new_combinations
                    
                    if not find_all and curr_sum + num_int == target_int:
                        return {target_int: new_combinations[:1]}
            
            dp.update(new_sums)
            
            # 更频繁的内存清理
            if i % 5 == 0:  # 每5个数字清理一次
                dp = {k: v[:100] for k, v in dp.items()  # 限制每个sum的组合数
                     if k + min_num <= target_int}
        
        return dp

    def _calculate_combinations_sequential(self, target: float) -> List[List[float]]:
        """单线程计算组合"""
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

def worker(chunk, target_int, find_all, shared_dict, stop_event):
    """工作进程函数"""
    if stop_event.is_set():
        return {}
        
    dp = {0: [[]]}
    min_num = min(chunk) * 100 if chunk else 0
    
    for i, num in enumerate(chunk):
        if stop_event.is_set():
            return {}
            
        num_int = int(round(num * 100))
        new_sums = {}
        
        for curr_sum, combinations in list(dp.items()):
            if curr_sum + num_int <= target_int:
                # 限制组合数量，最多存储100个组合
                new_combinations = [combo + [num] for combo in combinations][:100]
                if curr_sum + num_int in new_sums:
                    new_sums[curr_sum + num_int].extend(new_combinations)
                else:
                    new_sums[curr_sum + num_int] = new_combinations
                
                if not find_all and curr_sum + num_int == target_int:
                    return {target_int: new_combinations[:1]}
        
        dp.update(new_sums)
        
        # 更频繁的内存清理
        if i % 5 == 0:  # 每5个数字清理一次
            dp = {k: v[:100] for k, v in dp.items()  # 限制每个sum的组合数
                 if k + min_num <= target_int}
    
    return dp

if __name__ == "__main__":
    root = tk.Tk()
    app = NumberCombinationApp(root)
    root.mainloop()
