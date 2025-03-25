import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np

class NumberCombinationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("数字组合计算器")
        
        # 初始化变量
        self.numbers = []
        self.target = tk.DoubleVar(value=100.0)
        self.find_all = tk.BooleanVar(value=False)
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 目标值输入
        tk.Label(self.root, text="目标值:").grid(row=0, column=0, padx=5, pady=5)
        tk.Entry(self.root, textvariable=self.target).grid(row=0, column=1, padx=5, pady=5)
        
        # 选项
        tk.Checkbutton(self.root, text="查找所有组合", variable=self.find_all).grid(row=1, column=0, columnspan=2, pady=5)
        
        # 按钮
        tk.Button(self.root, text="导入数字", command=self.import_numbers).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(self.root, text="计算组合", command=self.find_combinations).grid(row=2, column=1, padx=5, pady=5)
        
        # 结果显示区域
        self.result_text = tk.Text(self.root, height=10, width=50)
        self.result_text.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
    def import_numbers(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    self.numbers = [float(num) for num in content.split() if num.replace('.', '').isdigit()]
                messagebox.showinfo("成功", f"已导入 {len(self.numbers)} 个数字")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {str(e)}")
    
    def find_combinations(self):
        target = self.target.get()
        if not self.numbers:
            messagebox.showwarning("警告", "请先导入数字列表")
            return
            
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"正在查找组合(目标值: {target})...\n")
        
        # 使用动态规划算法查找组合
        results = self.find_subset_sums(self.numbers, target)
        
        if not results:
            self.result_text.insert(tk.END, "未找到符合条件的组合")
        else:
            for i, combo in enumerate(results, 1):
                self.result_text.insert(tk.END, f"组合 {i}: {combo} (总和: {sum(combo):.2f})\n")
    
    def find_subset_sums(self, nums, target):
        if len(nums) > 50:
            self.result_text.insert(tk.END, "警告: 数字数量较多，计算可能需要较长时间\n")
            self.root.update()
        
        nums = [round(num, 2) for num in nums]
        target = round(target, 2)
        target_int = int(target * 100)
        
        # 优化内存的动态规划算法
        dp = [[] for _ in range(target_int + 1)]
        dp[0] = [()]
        
        for i, num in enumerate(nums):
            num_int = int(round(num * 100))
            for t in range(target_int, num_int - 1, -1):
                if dp[t - num_int]:
                    if not dp[t]:
                        dp[t] = []
                    for prev in dp[t - num_int]:
                        dp[t].append(prev + (num,))
                        # 如果不需要所有组合，找到一个就可以停止
                        if not self.find_all.get():
                            break
            
            # 更新进度显示
            progress = (i + 1) / len(nums) * 100
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"计算中... {progress:.1f}%\n")
            self.root.update()
            
            # 定期清理内存
            if i % 10 == 0:
                for t in range(target_int + 1):
                    if len(dp[t]) > 1 and not self.find_all.get():
                        dp[t] = dp[t][:1]
        
        if not dp[target_int]:
            return []
            
        if not self.find_all.get():
            return [dp[target_int][0]]
            
        return dp[target_int]

if __name__ == "__main__":
    root = tk.Tk()
    app = NumberCombinationApp(root)
    root.mainloop()
