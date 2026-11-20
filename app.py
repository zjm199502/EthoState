"""EthoState desktop entry point."""
import multiprocessing as mp
import os
import sys
import time
import traceback
import webbrowser
from pathlib import Path

VERSION = "1.0.0"
RELEASES = "https://github.com/zjm199502/EthoState/releases/latest"


def worker(sender, path):
    try:
        from analysis_core import analyze
        sender.send((True, analyze(path)))
    except Exception as exc:
        sender.send((False, str(exc)))
    finally:
        sender.close()


class Workspace:
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk
        self.root = root
        self.proc = self.receiver = self.timer = self.canvas = self.result = None
        self.root.title(f"EthoState   ·   动物行为分析   {VERSION}")
        self.root.geometry("1100x750")
        self.root.minsize(840, 620)
        self.root.configure(bg="#f3f6f4")
        self.root.iconbitmap(str(Path(__file__).with_name("ethostate.ico")))
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", padding=(12, 7), background="#edf3ef")
        style.configure("Action.TButton", foreground="white", background="#00786e")
        style.map("Action.TButton", background=[("active", "#005e56")])
        brand = tk.Frame(root, bg="#173d39", padx=24, pady=12)
        brand.pack(fill="x")
        tk.Label(brand, text="EthoState", font=("Segoe UI Semibold",22), fg="white", bg="#173d39").pack(side="left")
        tk.Label(brand, text="条件恐惧  /  Motion Index", fg="#c2dad2", bg="#173d39",
                 font=("Microsoft YaHei UI",11)).pack(side="left", padx=24)
        ttk.Button(brand, text="打开数据…", style="Action.TButton", command=self.open).pack(side="right")
        ttk.Button(brand, text="合成示例", command=lambda: self.start(None)).pack(side="right", padx=8)
        self.body = tk.Frame(root,bg="#f3f6f4",padx=20,pady=12)
        self.body.pack(fill="both",expand=True)
        self.heading = tk.StringVar(value="分析工作区")
        tk.Label(self.body,textvariable=self.heading,bg="#f3f6f4",fg="#173d39",anchor="w",
                 font=("Microsoft YaHei UI",16,"bold")).pack(fill="x")
        self.status = tk.StringVar(value="打开 XLSX 或 UTF-8 CSV 文件，或载入合成示例。")
        tk.Label(self.body,textvariable=self.status,bg="#f3f6f4",fg="#42635d",anchor="w").pack(fill="x",pady=(3,9))
        controls = tk.Frame(self.body,bg="#f3f6f4")
        controls.pack(fill="x")
        self.split = tk.StringVar()
        self.dt = tk.StringVar()
        for label, var in (("对照组列数",self.split),("采样间隔（秒，可留空）",self.dt)):
            tk.Label(controls,text=label,bg="#f3f6f4").pack(side="left")
            ttk.Entry(controls,textvariable=var,width=8).pack(side="left",padx=(4,12))
        ttk.Button(controls,text="应用",command=self.apply).pack(side="left")
        self.export_btn = ttk.Button(controls,text="导出结果包…",command=self.export,state="disabled")
        self.export_btn.pack(side="right")
        self.tabs = ttk.Notebook(self.body)
        self.tabs.pack(fill="both", expand=True, pady=10)
        self.pages = []
        for title in ("组间概览","单鼠轨迹","逐鼠汇总"):
            page = ttk.Frame(self.tabs)
            self.pages.append(page)
            self.tabs.add(page,text=title)
        self.mouse = ttk.Combobox(self.pages[1], state="readonly",width=30)
        self.mouse.pack(anchor="w", padx=8,pady=4)
        self.mouse.bind("<<ComboboxSelected>>",lambda _:self.draw())
        self.tabs.bind("<<NotebookTabChanged>>", lambda _:self.draw())
        self.tree = ttk.Treeview(self.pages[2],columns=("mouse","group","n","missing","mean","low","pct","bouts"),show="headings")
        for key, label in zip(self.tree["columns"],("小鼠","组别","有效点","缺失点","平均 MI","低运动点","低运动 %","低运动段")):
            self.tree.heading(key,text=label)
            self.tree.column(key,width=80,minwidth=45,anchor="center")
        bar = ttk.Scrollbar(self.pages[2],command=self.tree.yview)
        bar.pack(side="right",fill="y")
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(fill="both",expand=True)
        self.empty = ttk.Label(self.pages[0],text="每列一只鼠，每行一个等间隔采样点。\n\n打开数据后，软件将拟合共享的双状态 HMM。",justify="center")
        self.empty.place(relx=.5,rely=.5,anchor="center")
        footer = tk.Frame(self.body,bg="#f3f6f4")
        footer.pack(fill="x")
        tk.Label(footer,text="低运动状态的冻结行为解释需结合视频或人工评分校准。",bg="#f3f6f4",fg="#465e58").pack(side="left")
        ttk.Button(footer,text="版本与更新 ↗",command=lambda:webbrowser.open(RELEASES)).pack(side="right")
        root.protocol("WM_DELETE_WINDOW",self.close)

    def open(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("运动指数","*.xlsx *.csv")])
        if path:
            self.start(path)

    def stop(self):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.proc:
            if self.proc.is_alive():
                self.proc.terminate()
            self.proc.join()
            self.proc.close()
            self.proc = None
        if self.receiver:
            self.receiver.close()
            self.receiver = None

    def start(self, path):
        self.stop()
        self.receiver, sender = mp.Pipe(False)
        self.proc = mp.Process(target=worker,args=(sender,path),daemon=True)
        self.proc.start()
        sender.close()
        self.status.set("正在读取数据并拟合双状态 HMM…")
        self.export_btn.configure(state="disabled")
        self.timer = self.root.after(100,self.poll)

    def poll(self):
        from tkinter import messagebox
        self.timer = None
        if self.receiver.poll():
            try:
                ok, payload = self.receiver.recv()
            except EOFError:
                ok, payload = False, "分析进程意外退出。"
            self.stop()
            if ok:
                self.result = payload
                names = payload[0]
                self.heading.set(payload[-1]["source"])
                self.split.set(str(len(names)//2))
                self.dt.set("")
                self.mouse.configure(values=names)
                self.mouse.current(0)
                self.empty.place_forget()
                self.apply()
            else:
                self.status.set("导入失败。可修正文件后重新打开。")
                messagebox.showerror("分析失败",payload)
            self.export_btn.configure(state="normal" if self.result else "disabled")
        else:
            self.timer = self.root.after(100,self.poll)

    def apply(self):
        from tkinter import messagebox
        import math
        if self.result is None:
            return
        try:
            split = int(self.split.get())
            dt = float(self.dt.get()) if self.dt.get().strip() else None
            if not 1 <= split < len(self.result[0]) or (dt is not None and (dt <= 0 or not math.isfinite(dt))):
                raise ValueError
        except ValueError:
            messagebox.showerror("参数无效","两组各需至少一只鼠。采样间隔需为有限正数或留空。")
            return False
        self.applied = split, dt
        from report import summary
        self.tree.delete(*self.tree.get_children())
        for row in summary(self.result,split):
            name, group, valid, missing, mean, low, pct, bouts = row
            self.tree.insert("", "end", values=(name,"对照" if group=="Control" else "实验",valid,missing,f"{mean:.2f}",low,f"{pct:.2f}",bouts))
        names, raw, _, _, meta = self.result
        diagnosis = "已收敛" if meta["converged"] else "请复核收敛情况"
        if meta["low_equals_zero"]:
            diagnosis += "  ·  本次低运动点与零值完全重合"
        self.status.set(f"{len(names)} 只鼠  ·  {len(raw):,} 个采样点  ·  对照 {split} / 实验 {len(names)-split}  ·  HMM {meta['iterations']} 次迭代，{diagnosis}")
        self.draw()
        return True

    def draw(self):
        if self.result is None:
            return
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            self.canvas.figure.clear()
            self.canvas = None
        page = self.tabs.index("current")
        if page == 2:
            return
        from report import make_figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        fig = make_figure(self.result,*self.applied, self.mouse.current() if page else None)
        self.canvas = FigureCanvasTkAgg(fig,master=self.pages[page])
        self.canvas.get_tk_widget().pack(fill="both",expand=True)
        self.canvas.draw()

    def export(self):
        from tkinter import filedialog, messagebox
        if not self.apply():
            return
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("分析结果包","*.zip")],initialfile="EthoState-results.zip")
        if path:
            from report import export_bundle
            try:
                export_bundle(path,self.result,*self.applied,self.mouse.current())
                messagebox.showinfo("导出完成",path)
            except Exception as exc:
                messagebox.showerror("导出失败",str(exc))

    def close(self):
        self.stop()
        self.result = None
        if self.canvas:
            self.canvas.figure.clear()
        self.root.destroy()


def main():
    mp.freeze_support()
    import tkinter as tk
    root = tk.Tk()
    ui = Workspace(root)
    if len(sys.argv) == 4 and sys.argv[1] == "--verify":
        # Exercise the installed GUI, worker and exports unattended.
        from report import export_bundle
        from tkinter import messagebox
        def fail(title, message):
            raise RuntimeError(f"{title}: {message}")
        messagebox.showerror = fail
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda *args: errors.append("".join(traceback.format_exception(*args)))
        try:
            ui.start(None)
            ui.start(sys.argv[2])
            deadline = time.monotonic() + 300
            while ui.proc and time.monotonic() < deadline and not errors:
                root.update()
                time.sleep(.04)
            if errors or ui.result is None:
                raise RuntimeError("".join(errors) or "Analysis timed out")
            ui.tabs.select(1)
            root.update()
            export_bundle(sys.argv[3],ui.result,*ui.applied,ui.mouse.current())
            ui.start(None)
        except Exception:
            Path(sys.argv[3]+".error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        finally:
            ui.close()
    else:
        if len(sys.argv)==2:
            ui.start(sys.argv[1])
        root.mainloop()


if __name__ == "__main__":
    main()

