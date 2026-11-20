"""Import motion matrices and fit one shared HMM across independent sequences."""
import csv
import hashlib
from pathlib import Path

import numpy as np
from hmmlearn.hmm import GaussianHMM
from openpyxl import load_workbook


def read_matrix(path):
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        book = load_workbook(path, read_only=True, data_only=True)
        try:
            sheet = book.worksheets[0]
            rows = list(sheet.values)
            source_sheet = sheet.title
        finally:
            book.close()
    else:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.reader(stream))
        source_sheet = None

    def present(cell):
        return cell is not None and str(cell).strip() != ""

    while rows and not any(map(present, rows[-1])):
        rows.pop()
    width = max((i + 1 for row in rows for i, cell in enumerate(row) if present(cell)), default=0)
    if width < 2:
        raise ValueError("需要至少两列小鼠数据。")
    first = rows[0][:width]

    def numeric(cell):
        try:
            float(cell)
            return True
        except (ValueError, TypeError):
            return False

    header = len(first) == width and all(isinstance(x, str) and present(x) and not numeric(x) for x in first)
    names = list(map(str, first)) if header else [f"Mouse {i + 1:02d}" for i in range(width)]
    if len(set(names)) != width:
        raise ValueError("小鼠列名需要唯一。")
    matrix = np.full((len(rows) - int(header), width), np.nan)
    for i, row in enumerate(rows[int(header):]):
        for j, cell in enumerate(row[:width]):
            if present(cell):
                msg = f"第 {i + 1 + int(header)} 行、第 {j + 1} 列需要非负数值。"
                if not numeric(cell) or isinstance(cell, bool):
                    raise ValueError(msg)
                value = float(cell)
                if not np.isfinite(value) or value < 0:
                    raise ValueError(msg)
                matrix[i, j] = value
    if np.any(np.isfinite(matrix).sum(axis=0) < 2):
        raise ValueError("每只鼠至少需要两个有效采样点，请检查空列或表头。")
    return names, matrix, source_sheet


def demo():
    rng = np.random.default_rng(79)
    matrix = np.empty((600, 10))
    for j in range(10):
        low = False
        for i in range(600):
            if rng.random() < (0.045 if low else (0.035 if j < 5 else 0.085)):
                low = not low
            matrix[i, j] = rng.poisson(8 if low else 95)
    return [f"Mouse {i:02d}" for i in range(1, 11)], matrix, None


def analyze(path=None):
    names, raw, sheet = read_matrix(path) if path else demo()
    pieces = []
    coords = []
    for mouse, series in enumerate(raw.T):
        edges = np.diff(np.r_[False, np.isfinite(series), False].astype(int))
        for start, end in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
            pieces.append(np.log1p(series[start:end]))
            coords.append((mouse, start, end))
    lengths = [len(x) for x in pieces]
    x = np.concatenate(pieces)[:, None]
    if len(x) < 20 or np.ptp(x) < 1e-7 or max(lengths) < 2:
        raise ValueError("HMM 需要至少 20 个有效点、连续观测和可区分的运动水平。")
    best = None
    for quantiles in ((0.2, 0.8), (0.05, 0.95)):
        model = GaussianHMM(n_components=2, covariance_type="diag", n_iter=100, tol=0.01,
                            init_params="", transmat_prior=1.01, startprob_prior=1.01)
        model.startprob_ = np.array([0.5, 0.5])
        model.transmat_ = np.array([[0.95, 0.05], [0.05, 0.95]])
        model.means_ = np.quantile(x, quantiles).reshape(2, 1)
        model.covars_ = np.full((2, 1), max(float(x.var()), .01))
        try:
            model.fit(x, lengths)
            score = model.score(x, lengths)
        except (ValueError, FloatingPointError):
            continue
        if np.isfinite(score) and (best is None or score > best[0]):
            best = score, model
    if best is None:
        raise ValueError("无法拟合两个状态，请检查数据的变化范围。")
    score, model = best
    order = np.argsort(model.means_.ravel())
    decoded = np.argsort(order)[model.predict(x, lengths)]
    if len(np.unique(decoded)) != 2 or np.ptp(model.means_) < 1e-7:
        raise ValueError("模型没有分辨出两种运动状态。")
    posterior = model.predict_proba(x, lengths)[:, order[0]]
    states = np.full(raw.shape, -1, dtype=np.int8)
    probability = np.full(raw.shape, np.nan)
    offset = 0
    for mouse, start, end in coords:
        stop = offset + end - start
        states[start:end, mouse] = decoded[offset:stop]
        probability[start:end, mouse] = posterior[offset:stop]
        offset = stop
    history = list(model.monitor_.history)
    info = dict(version="1.0.1", source=Path(path).name if path else "Synthetic demo",
                sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest() if path else None,
                sheet=sheet, transformation="log1p", state_order=["low", "high"],
                mean_log1p=model.means_.ravel()[order].tolist(),
                variance_log1p=model.covars_.ravel()[order].tolist(),
                start=model.startprob_[order].tolist(), transition=model.transmat_[np.ix_(order, order)].tolist(),
                sequences=len(coords), iterations=len(history), log_likelihood=score,
                converged=len(history) >= 2 and abs(history[-1] - history[-2]) < model.tol)
    valid = states >= 0
    info["zero_fraction"] = float(np.mean(raw[valid] == 0))
    info["low_equals_zero"] = bool(np.array_equal(states[valid] == 0, raw[valid] == 0))
    return names, raw, states, probability, info

