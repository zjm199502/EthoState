# EthoState

用于 MED 条件恐惧实验的 Windows 桌面分析工具。从每只鼠的 motion index 序列估计低运动和高运动状态，查看逐鼠轨迹，并比较两组低运动占比。

**[下载 Windows x64 安装程序](https://github.com/zjm199502/EthoState/releases/latest/download/EthoState-1.0.0-Windows-x64-Setup.exe)** · [正式版本](https://github.com/zjm199502/EthoState/releases)

### 开始分析

1. 双击安装程序，从开始菜单打开 EthoState。点击「合成示例」可以先试用全流程。
2. 在「打开数据」选择 XLSX 或 UTF-8 CSV。XLSX 读取第一个工作表。每列一只鼠，每行对应一个等间隔采样点。可使用全为文本且唯一的第一行作鼠名，数字型首行会计入观测。输入表仅放运动指数列。公式请先转成数值。
3. 默认前 ⌊鼠数/2⌋ 列为对照组，其他列为实验组。可修改「对照组列数」后点击「应用」。已知采样间隔时填写秒数。留空时以从 0 开始的采样点编号绘图。
4. 「组间概览」热图按原始列顺序显示状态，橙线分组。右侧每个点代表一只鼠，短横线为组内均值。「单鼠轨迹」可切换小鼠，同时查看原始信号、低运动后验概率和解码结果。
5. 「导出结果包」保存 ZIP，内含全组和当前小鼠图（300 dpi PNG、矢量 SVG）、逐样本 `observations.csv`、逐鼠 `mice.csv`、分组 `groups.csv` 和模型参数 `model.json`。CSV 的空状态表示缺失。JSON 记录源文件名、SHA-256、鼠列顺序、采样间隔、迭代诊断及转移矩阵。

### 模型与结果解释

使用 log1p(motion index) 拟合两状态一维高斯 HMM。所有小鼠共享模型，每只鼠和每段连续有效记录分别初始化。缺失处断开，原采样位置保留。两套确定性分位数初值分别进行最多 100 次 EM 迭代，以较高对数似然的模型进行 Viterbi 解码。发射均值较小的状态标记为低运动。后验概率来自前向后向算法。收敛标志要求末两次对数似然变化绝对值小于 0.01。模型实现见 [hmmlearn 文档](https://hmmlearn.readthedocs.io/en/stable/tutorial.html)。

逐鼠低运动占比为低运动解码点数除以该鼠有效点数。连续低运动段遇到缺失即终止。组均值以鼠为单位等权计算，SD 为样本标准差。低运动可作为冻结候选指标，具体实验的行为判定应结合视频或人工标注校准。不同设备的运动指数标度、记录条件和采样频率应在合并拟合前核对。

### 从源码运行和打包

使用 Windows x64、Python 3.11 和 Tcl/Tk。在仓库目录运行以下 PowerShell 命令。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m unittest
.\.venv\Scripts\python app.py
```

安装 Inno Setup 6 后运行 `./build.ps1`。完整安装包位于 `release/`。安装程序支持当前用户安装、开始菜单入口和系统卸载。应用的「版本与更新」打开最新正式发布页。后续版本可通过运行新安装程序就地升级。


