from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from functools import reduce
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ============================================================
# PERSONAL EXPENSE ANALYTICS & BUDGET MANAGEMENT SYSTEM
# OOP + Pandas + NumPy + Matplotlib + Tkinter + SQLite + CSV
# ============================================================

APP_TITLE = "Personal Expense Analytics"
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "expenses.db"
DEMO_FILE = BASE_DIR / "expense_730_days.csv"
DATE_FORMAT = "%Y-%m-%d"

CATEGORIES = [
    "Food", "Transport", "Education", "Entertainment", "Utilities",
    "Shopping", "Rent", "Health", "Personal Care", "Other"
]

DEFAULT_BUDGETS = {
    "Food": 5000,
    "Transport": 2500,
    "Education": 2500,
    "Entertainment": 2000,
    "Utilities": 1800,
    "Shopping": 3500,
    "Rent": 10000,
    "Health": 2000,
    "Personal Care": 1500,
    "Other": 1000,
}

# ---------- Vibrant, professional palette ----------
NAVY = "#16213E"
NAVY_2 = "#1F3A5F"
BLUE = "#3B82F6"
SKY = "#38BDF8"
TEAL = "#14B8A6"
PURPLE = "#8B5CF6"
PINK = "#EC4899"
GOLD = "#F59E0B"
RED = "#EF4444"
GREEN = "#22C55E"
BG = "#F5F7FB"
CARD = "#FFFFFF"
TEXT = "#172033"
MUTED = "#718096"
BORDER = "#E3E8F0"
SOFT_BLUE = "#EEF5FF"
SOFT_TEAL = "#EAFBF7"
SOFT_PURPLE = "#F4F0FF"
SOFT_GOLD = "#FFF7E8"
SOFT_PINK = "#FFF0F7"
SOFT_RED = "#FFF0F0"

CATEGORY_COLORS = {
    "Food": BLUE,
    "Transport": TEAL,
    "Education": PURPLE,
    "Entertainment": GOLD,
    "Utilities": RED,
    "Shopping": PINK,
    "Rent": "#64748B",
    "Health": GREEN,
    "Personal Care": "#F97316",
    "Other": "#94A3B8",
}


# ============================================================
# OOP MODEL
# ============================================================
class Transaction:
    def __init__(self, date, category, amount, description):
        self.date = str(date)
        self.category = str(category)
        self.amount = float(amount)
        self.description = str(description).strip()

    @staticmethod
    def valid_date(date_text):
        try:
            datetime.strptime(str(date_text), DATE_FORMAT)
            return True
        except ValueError:
            return False

    def to_tuple(self):
        return self.date, self.category, self.amount, self.description


class Budget:
    def __init__(self, category, limit):
        self.category = category
        self.limit = float(limit)

    def status(self, spent):
        spent = float(spent)
        if self.limit <= 0:
            return "NO BUDGET"
        if spent > self.limit:
            return "OVER BUDGET"
        if spent >= self.limit * 0.80:
            return "NEAR LIMIT"
        return "WITHIN BUDGET"


# ============================================================
# SQLITE STORAGE
# ============================================================
class Database:
    def __init__(self, db_path=DB_FILE):
        self.db_path = Path(db_path)
        self.create_tables()
        self.insert_default_budgets()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        with self.connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT
                )"""
            )
            con.execute(
                """CREATE TABLE IF NOT EXISTS budgets (
                    category TEXT PRIMARY KEY,
                    limit_amount REAL NOT NULL
                )"""
            )

            # Migrate an older project database safely.
            columns = [r[1] for r in con.execute("PRAGMA table_info(budgets)").fetchall()]
            if columns and "limit_amount" not in columns:
                old_value = next(
                    (name for name in ("budget", "limit", "amount", "budget_amount") if name in columns),
                    None,
                )
                if "category" in columns and old_value:
                    con.execute("ALTER TABLE budgets RENAME TO budgets_old")
                    con.execute("CREATE TABLE budgets (category TEXT PRIMARY KEY, limit_amount REAL NOT NULL)")
                    con.execute(
                        f"INSERT OR IGNORE INTO budgets(category, limit_amount) "
                        f"SELECT category, {old_value} FROM budgets_old"
                    )
                    con.execute("DROP TABLE budgets_old")

    def insert_default_budgets(self):
        with self.connect() as con:
            for category, limit_amount in DEFAULT_BUDGETS.items():
                con.execute(
                    "INSERT OR IGNORE INTO budgets(category, limit_amount) VALUES (?, ?)",
                    (category, limit_amount),
                )

    def add_transaction(self, transaction):
        with self.connect() as con:
            con.execute(
                "INSERT INTO transactions(date, category, amount, description) VALUES (?, ?, ?, ?)",
                transaction.to_tuple(),
            )

    def replace_transactions(self, transactions):
        with self.connect() as con:
            con.execute("DELETE FROM transactions")
            con.executemany(
                "INSERT INTO transactions(date, category, amount, description) VALUES (?, ?, ?, ?)",
                [t.to_tuple() for t in transactions],
            )

    def get_transactions(self):
        with self.connect() as con:
            rows = con.execute(
                "SELECT date, category, amount, description FROM transactions ORDER BY date"
            ).fetchall()
        return [Transaction(*row) for row in rows]

    def get_budgets(self):
        with self.connect() as con:
            rows = con.execute("SELECT category, limit_amount FROM budgets").fetchall()
        return {category: Budget(category, amount) for category, amount in rows}

    def save_budget(self, category, limit_amount):
        with self.connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO budgets(category, limit_amount) VALUES (?, ?)",
                (category, float(limit_amount)),
            )


# ============================================================
# CUSTOM ITERATOR
# ============================================================
class TransactionIterator:
    def __init__(self, transactions):
        self.transactions = transactions
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.transactions):
            raise StopIteration
        item = self.transactions[self.index]
        self.index += 1
        return item


# ============================================================
# ANALYTICS
# ============================================================
class ExpenseAnalytics:
    def __init__(self, transactions):
        self.transactions = transactions
        self.df = self._to_dataframe()

    def _to_dataframe(self):
        records = list(
            map(
                lambda t: {
                    "date": t.date,
                    "category": t.category,
                    "amount": t.amount,
                    "description": t.description,
                },
                self.transactions,
            )
        )
        return pd.DataFrame(records, columns=["date", "category", "amount", "description"])

    def total_spending(self):
        if self.df.empty:
            return 0.0
        return float(np.sum(self.df["amount"].to_numpy(dtype=float)))

    def average_spending(self):
        if self.df.empty:
            return 0.0
        return float(np.mean(self.df["amount"].to_numpy(dtype=float)))

    def largest_expense(self):
        if self.df.empty:
            return 0.0
        return float(np.max(self.df["amount"].to_numpy(dtype=float)))

    def reduced_total(self):
        return reduce(lambda a, b: a + b, [t.amount for t in self.transactions], 0.0)

    def month_list(self):
        if self.df.empty:
            return []
        months = pd.to_datetime(self.df["date"]).dt.to_period("M").astype(str).unique().tolist()
        return sorted(months)

    def latest_month(self):
        months = self.month_list()
        return months[-1] if months else "-"

    def month_df(self, month):
        if self.df.empty or not month or month == "-":
            return self.df.iloc[0:0].copy()
        temp = self.df.copy()
        temp["month"] = pd.to_datetime(temp["date"]).dt.to_period("M").astype(str)
        return temp[temp["month"] == month].copy()

    def month_total(self, month):
        frame = self.month_df(month)
        return float(frame["amount"].sum()) if not frame.empty else 0.0

    def month_transaction_count(self, month):
        return int(len(self.month_df(month)))

    def top_category(self, month=None):
        frame = self.month_df(month) if month else self.df
        if frame.empty:
            return "-"
        totals = frame.groupby("category")["amount"].sum().sort_values(ascending=False)
        return str(totals.index[0]) if not totals.empty else "-"

    def category_totals(self, month=None):
        frame = self.month_df(month) if month else self.df
        if frame.empty:
            return pd.Series(dtype=float)
        return frame.groupby("category")["amount"].sum().sort_values(ascending=False)

    def daily_totals(self, month=None):
        frame = self.month_df(month) if month else self.df
        if frame.empty:
            return pd.Series(dtype=float)
        return frame.groupby("date")["amount"].sum().sort_index()

    def monthly_totals(self):
        if self.df.empty:
            return pd.Series(dtype=float)
        temp = self.df.copy()
        temp["month"] = pd.to_datetime(temp["date"]).dt.to_period("M").astype(str)
        return temp.groupby("month")["amount"].sum().sort_index()


# ============================================================
# REUSABLE GUI COMPONENTS
# ============================================================
class MetricCard(tk.Frame):
    def __init__(self, master, title, value, note, accent, icon):
        super().__init__(master, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        self.configure(height=112)
        self.pack_propagate(False)

        top = tk.Frame(self, bg=CARD)
        top.pack(fill="x", padx=16, pady=(14, 0))
        icon_box = tk.Frame(top, bg=accent, width=30, height=30)
        icon_box.pack(side="left")
        icon_box.pack_propagate(False)
        tk.Label(icon_box, text=icon, fg="white", bg=accent, font=("Segoe UI", 12, "bold")).pack(expand=True)
        tk.Label(top, text=title, font=("Segoe UI", 8, "bold"), fg=MUTED, bg=CARD).pack(side="left", padx=9)

        self.value_label = tk.Label(self, text=value, font=("Segoe UI", 19, "bold"), fg=TEXT, bg=CARD)
        self.value_label.pack(anchor="w", padx=16, pady=(5, 0))
        self.note_label = tk.Label(self, text=note, font=("Segoe UI", 8), fg=MUTED, bg=CARD)
        self.note_label.pack(anchor="w", padx=16)


class ActionCard(tk.Frame):
    """Clickable dashboard action card.

    The whole card is clickable, including the icon and both text labels.
    The previous version only bound the outer frames, so clicks on the child
    labels could appear to do nothing. Recursive binding fixes that while
    keeping the visual design simple and fully Tkinter-based.
    """
    def __init__(self, master, title, subtitle, icon, accent, command):
        super().__init__(master, bg=CARD, highlightbackground=BORDER, highlightthickness=1, cursor="hand2")
        self.command = command
        self.accent = accent
        self.configure(width=180, height=92)
        self.pack_propagate(False)

        box = tk.Frame(self, bg=accent, width=36, height=36, cursor="hand2")
        box.pack(side="left", padx=14)
        box.pack_propagate(False)
        self.icon_frame = box
        icon_label = tk.Label(box, text=icon, font=("Segoe UI", 14, "bold"), fg="white", bg=accent, cursor="hand2")
        icon_label.pack(expand=True, fill="both")

        text = tk.Frame(self, bg=CARD, cursor="hand2")
        text.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.text_frame = text
        title_label = tk.Label(
            text, text=title, font=("Segoe UI", 9, "bold"), fg=TEXT, bg=CARD,
            cursor="hand2"
        )
        title_label.pack(anchor="w", pady=(15, 2))
        subtitle_label = tk.Label(
            text, text=subtitle, font=("Segoe UI", 8), fg=MUTED, bg=CARD,
            wraplength=118, justify="left", cursor="hand2"
        )
        subtitle_label.pack(anchor="w")

        # Bind every descendant, not only the outer frames. This ensures
        # clicking directly on the icon/title/subtitle triggers the action.
        self._bind_recursive(self)

    def _bind_recursive(self, widget):
        widget.bind("<ButtonRelease-1>", self._click, add="+")
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")
        try:
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._bind_recursive(child)

    def _click(self, _event=None):
        self.command()

    def _enter(self, _event=None):
        hover = "#F8FBFF"
        self.configure(bg=hover)
        self.text_frame.configure(bg=hover)
        for child in self.text_frame.winfo_children():
            try:
                child.configure(bg=hover)
            except tk.TclError:
                pass

    def _leave(self, _event=None):
        self.configure(bg=CARD)
        self.text_frame.configure(bg=CARD)
        for child in self.text_frame.winfo_children():
            try:
                child.configure(bg=CARD)
            except tk.TclError:
                pass


# ============================================================
# MAIN APPLICATION
# ============================================================
class ExpenseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1440x920")
        self.minsize(1220, 800)
        self.configure(bg=BG)

        self.db = Database()
        self.analytics = ExpenseAnalytics(self.db.get_transactions())
        self.current_page = "Dashboard"
        self.nav_buttons = {}
        self.analytics_mode = "Monthly Trend"
        self.selected_analytics_month = "All"
        self.selected_budget_month = self.analytics.latest_month()
        self.selected_report_month = self.analytics.latest_month()

        self._setup_style()
        self._build_layout()
        self.show_page("Dashboard")

    # --------------------------------------------------------
    # Style
    # --------------------------------------------------------
    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview", background=CARD, foreground=TEXT, fieldbackground=CARD,
            rowheight=31, borderwidth=0, font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading", background="#EEF2F7", foreground=TEXT,
            font=("Segoe UI", 9, "bold"), relief="flat"
        )
        style.map("Treeview", background=[("selected", "#E5EEFF")], foreground=[("selected", TEXT)])
        style.configure("TCombobox", padding=5, font=("Segoe UI", 9))
        style.configure(
            "Analytics.TCombobox",
            padding=6,
            font=("Segoe UI", 10, "bold"),
            foreground=TEXT,
            fieldbackground=CARD,
            background=CARD,
            arrowcolor=NAVY_2,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
        )
        style.map(
            "Analytics.TCombobox",
            fieldbackground=[("readonly", CARD), ("disabled", "#F2F4F7")],
            foreground=[("readonly", TEXT), ("disabled", MUTED)],
            selectbackground=[("readonly", SOFT_BLUE)],
            selectforeground=[("readonly", TEXT)],
        )
        style.configure("Horizontal.TProgressbar", troughcolor="#EDF1F5", background=BLUE, thickness=8)

    # --------------------------------------------------------
    # Layout
    # --------------------------------------------------------
    def _build_layout(self):
        self.sidebar = tk.Frame(self, bg=NAVY, width=245)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Brand
        brand = tk.Frame(self.sidebar, bg=NAVY)
        brand.pack(fill="x", padx=20, pady=(22, 20))
        logo = tk.Frame(brand, bg=TEAL, width=40, height=40)
        logo.pack(side="left")
        logo.pack_propagate(False)
        tk.Label(logo, text="₹", font=("Segoe UI", 18, "bold"), fg="white", bg=TEAL).pack(expand=True)
        title_box = tk.Frame(brand, bg=NAVY)
        title_box.pack(side="left", padx=10)
        tk.Label(title_box, text="Expense", font=("Segoe UI", 17, "bold"), fg="white", bg=NAVY).pack(anchor="w")
        tk.Label(title_box, text="ANALYTICS", font=("Segoe UI", 8, "bold"), fg="#9FB6C9", bg=NAVY).pack(anchor="w")

        tk.Frame(self.sidebar, bg="#284562", height=1).pack(fill="x", padx=18, pady=(0, 14))
        tk.Label(self.sidebar, text="WORKSPACE", font=("Segoe UI", 8, "bold"), fg="#819AB1", bg=NAVY).pack(anchor="w", padx=20, pady=(0, 8))

        nav_items = [
            ("▦", "Dashboard"),
            ("≡", "Transactions"),
            ("◔", "Analytics"),
            ("◉", "Budget"),
            ("▤", "Reports"),
        ]
        for icon, name in nav_items:
            self._create_nav_button(icon, name)

        # Sidebar footer
        footer = tk.Frame(self.sidebar, bg="#193452", highlightbackground="#284A68", highlightthickness=1)
        footer.pack(side="bottom", fill="x", padx=14, pady=15)
        tk.Label(footer, text="ADVANCED PYTHON PROJECT", font=("Segoe UI", 7, "bold"), fg="#A9C7DA", bg="#193452").pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(footer, text="OOP  •  Pandas  •  Tkinter\nSQLite  •  Matplotlib", font=("Segoe UI", 8), fg="#E4EEF6", bg="#193452", justify="left").pack(anchor="w", padx=12, pady=(0, 10))

        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        # Header
        self.header = tk.Frame(main, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        self.header.pack(fill="x", padx=20, pady=(16, 12))
        self.header.configure(height=78)
        self.header.pack_propagate(False)

        self.header_left = tk.Frame(self.header, bg=CARD)
        self.header_left.pack(side="left", padx=20)
        self.page_title = tk.Label(self.header_left, text="Dashboard", font=("Segoe UI", 19, "bold"), fg=TEXT, bg=CARD)
        self.page_title.pack(anchor="w", pady=(10, 0))
        self.page_subtitle = tk.Label(self.header_left, text="Your spending at a glance", font=("Segoe UI", 9), fg=MUTED, bg=CARD)
        self.page_subtitle.pack(anchor="w")

        right = tk.Frame(self.header, bg=CARD)
        right.pack(side="right", padx=18, pady=12)
        self.month_pill = tk.Label(right, text="", font=("Segoe UI", 8, "bold"), fg=NAVY_2, bg=SOFT_BLUE, padx=12, pady=6)
        self.month_pill.pack(side="left", padx=(0, 8))
        self._header_button(right, "＋ Add", self.open_add_expense, TEAL)
        self._header_button(right, "⇩ Import", self.import_csv, NAVY_2)
        self._header_button(right, "Demo Data", self.load_demo_data, GOLD)

        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=20, pady=(0, 18))

    def _create_nav_button(self, icon, text):
        btn = tk.Button(
            self.sidebar, text=f"  {icon}   {text}",
            command=lambda page=text: self.show_page(page),
            anchor="w", bg=NAVY, fg="#C8D7E2", activebackground=NAVY_2,
            activeforeground="white", relief="flat", bd=0,
            font=("Segoe UI", 10), padx=14, pady=10, cursor="hand2"
        )
        btn.pack(fill="x", padx=12, pady=2)
        self.nav_buttons[text] = btn

    def _header_button(self, parent, text, command, color):
        tk.Button(
            parent, text=text, command=command, bg=color, fg="white",
            activebackground=color, activeforeground="white", relief="flat", bd=0,
            font=("Segoe UI", 9, "bold"), padx=10, pady=7, cursor="hand2"
        ).pack(side="left", padx=3)

    def _set_header(self, title, subtitle):
        self.page_title.config(text=title)
        self.page_subtitle.config(text=subtitle)

    def _clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _update_month_pill(self):
        month = self.analytics.latest_month()
        self.month_pill.config(text=f"LATEST  {month}")

    def show_page(self, page):
        self.current_page = page
        self.analytics = ExpenseAnalytics(self.db.get_transactions())
        months = self.analytics.month_list()
        latest = self.analytics.latest_month()
        if self.selected_analytics_month != "All" and self.selected_analytics_month not in months:
            self.selected_analytics_month = latest
        if self.selected_budget_month not in months:
            self.selected_budget_month = latest
        if self.selected_report_month not in months:
            self.selected_report_month = latest
        self._update_month_pill()

        for name, button in self.nav_buttons.items():
            if name == page:
                button.config(bg=NAVY_2, fg="white", font=("Segoe UI", 10, "bold"))
            else:
                button.config(bg=NAVY, fg="#C8D7E2", font=("Segoe UI", 10))

        self._clear_content()
        pages = {
            "Dashboard": ("Dashboard", "Your spending at a glance", self._show_dashboard),
            "Transactions": ("Transactions", "Search, filter, add and manage every expense", self._show_transactions),
            "Analytics": ("Analytics", "Interactive charts for deeper spending analysis", self._show_analytics),
            "Budget": ("Budget", "Control monthly category limits and track usage", self._show_budget),
            "Reports": ("Reports", "Create a simple monthly spending summary", self._show_reports),
        }
        title, subtitle, builder = pages[page]
        self._set_header(title, subtitle)
        builder()

    # ========================================================
    # COMMON UI HELPERS
    # ========================================================
    def _panel(self, parent, title, subtitle=None):
        panel = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        top = tk.Frame(panel, bg=CARD)
        top.pack(fill="x", padx=16, pady=(14, 7))
        tk.Label(top, text=title, font=("Segoe UI", 11, "bold"), fg=TEXT, bg=CARD).pack(anchor="w")
        if subtitle:
            tk.Label(top, text=subtitle, font=("Segoe UI", 8), fg=MUTED, bg=CARD).pack(anchor="w", pady=(2, 0))
        return panel

    def _section_title(self, parent, title, subtitle=""):
        tk.Label(parent, text=title, font=("Segoe UI", 12, "bold"), fg=TEXT, bg=BG).pack(anchor="w")
        if subtitle:
            tk.Label(parent, text=subtitle, font=("Segoe UI", 8), fg=MUTED, bg=BG).pack(anchor="w", pady=(1, 8))

    def _progress_row(self, parent, name, spent, budget, accent):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=5)
        top = tk.Frame(row, bg=CARD)
        top.pack(fill="x")
        tk.Label(top, text=name, font=("Segoe UI", 8, "bold"), fg=TEXT, bg=CARD).pack(side="left")
        used = 0 if budget <= 0 else (spent / budget) * 100
        used_text = f"{used:.0f}%"
        tk.Label(top, text=used_text, font=("Segoe UI", 8, "bold"), fg=accent, bg=CARD).pack(side="right")
        bar = tk.Canvas(row, height=8, bg=CARD, highlightthickness=0)
        bar.pack(fill="x", pady=(4, 2))
        bar.update_idletasks()
        width = max(bar.winfo_width(), 200)
        bar.create_rectangle(0, 1, width, 7, fill="#EDF1F5", outline="")
        fill_width = min(width, width * min(used / 100, 1))
        bar.create_rectangle(0, 1, fill_width, 7, fill=accent, outline="")
        tk.Label(row, text=f"₹{spent:,.0f} spent  •  ₹{budget:,.0f} budget", font=("Segoe UI", 7), fg=MUTED, bg=CARD).pack(anchor="w")

    # ========================================================
    # DASHBOARD
    # ========================================================
    def _show_dashboard(self):
        tx = self.analytics.transactions
        total = self.analytics.total_spending()
        avg = self.analytics.average_spending()
        largest = self.analytics.largest_expense()
        count = len(tx)
        month = self.analytics.latest_month()
        month_total = self.analytics.month_total(month)
        top_category = self.analytics.top_category(month)
        budget_total = sum(b.limit for b in self.db.get_budgets().values())
        remaining = budget_total - month_total
        used = 0 if budget_total == 0 else month_total / budget_total * 100

        # Welcome banner
        hero = tk.Frame(self.content, bg=NAVY_2, highlightbackground=NAVY_2, highlightthickness=1)
        hero.pack(fill="x", pady=(0, 12))
        left = tk.Frame(hero, bg=NAVY_2)
        left.pack(side="left", padx=20, pady=15)
        tk.Label(left, text="PERSONAL FINANCE DASHBOARD", font=("Segoe UI", 8, "bold"), fg="#9ADCE0", bg=NAVY_2).pack(anchor="w")
        tk.Label(left, text="Know where your money goes.", font=("Segoe UI", 18, "bold"), fg="white", bg=NAVY_2).pack(anchor="w", pady=(2, 2))
        tk.Label(left, text=f"Latest month: {month}  •  Top category: {top_category}", font=("Segoe UI", 9), fg="#D7E6F0", bg=NAVY_2).pack(anchor="w")
        right = tk.Frame(hero, bg=NAVY_2)
        right.pack(side="right", padx=22, pady=14)
        tk.Label(right, text="MONTH SPENDING", font=("Segoe UI", 8, "bold"), fg="#9FB7CA", bg=NAVY_2).pack(anchor="e")
        tk.Label(right, text=f"₹{month_total:,.0f}", font=("Segoe UI", 22, "bold"), fg="white", bg=NAVY_2).pack(anchor="e")

        # KPI cards
        kpi = tk.Frame(self.content, bg=BG)
        kpi.pack(fill="x", pady=(0, 12))
        for i in range(4):
            kpi.grid_columnconfigure(i, weight=1)
        MetricCard(kpi, "TOTAL SPENDING", f"₹{total:,.0f}", f"Across {count:,} transactions", BLUE, "₹").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        MetricCard(kpi, "AVERAGE EXPENSE", f"₹{avg:,.0f}", "Average per transaction", TEAL, "≈").grid(row=0, column=1, sticky="ew", padx=5)
        MetricCard(kpi, "LARGEST EXPENSE", f"₹{largest:,.0f}", "Highest single expense", GOLD, "↗").grid(row=0, column=2, sticky="ew", padx=5)
        MetricCard(kpi, "BUDGET REMAINING", f"₹{remaining:,.0f}", f"{used:.0f}% of monthly budget used", GREEN if remaining >= 0 else RED, "✓" if remaining >= 0 else "!").grid(row=0, column=3, sticky="ew", padx=(5, 0))

        # Quick actions
        action_title = tk.Frame(self.content, bg=BG)
        action_title.pack(fill="x")
        self._section_title(action_title, "Quick Actions", "Common tasks you can open directly from the dashboard")
        actions = tk.Frame(self.content, bg=BG)
        actions.pack(fill="x", pady=(0, 12))
        ActionCard(actions, "Add Expense", "Record a new transaction", "+", TEAL, self.open_add_expense).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ActionCard(actions, "View Analytics", "Explore monthly and category charts", "◔", PURPLE, lambda: self.show_page("Analytics")).pack(side="left", fill="x", expand=True, padx=6)
        ActionCard(actions, "Manage Budget", "Set limits and check status", "◉", GOLD, lambda: self.show_page("Budget")).pack(side="left", fill="x", expand=True, padx=6)
        ActionCard(actions, "Import Data", "Load a CSV expense file", "⇩", BLUE, self.import_csv).pack(side="left", fill="x", expand=True, padx=(6, 0))

        # Main analytical area
        main = tk.Frame(self.content, bg=BG)
        main.pack(fill="both", expand=True)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        category_panel = self._panel(main, "Spending by Category", "Latest month category breakdown")
        category_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._dashboard_category_bars(category_panel, month)

        budget_panel = self._panel(main, "Budget Control", "How much of your monthly budget is being used")
        budget_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._dashboard_budget(budget_panel, month)

        # Bottom row: recent activity + insight
        bottom = tk.Frame(self.content, bg=BG)
        bottom.pack(fill="both", expand=True, pady=(12, 0))
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=2)
        bottom.grid_rowconfigure(0, weight=1)

        recent = self._panel(bottom, "Recent Activity", "Latest recorded expenses")
        recent.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._fill_recent_table(recent, tx)

        insight = self._panel(bottom, "Smart Insights", "Simple observations from your current data")
        insight.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._fill_insights(insight, month)

    def _dashboard_category_bars(self, panel, month):
        body = tk.Frame(panel, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        totals = self.analytics.category_totals(month)
        if totals.empty:
            tk.Label(body, text="No category data available.", font=("Segoe UI", 9), fg=MUTED, bg=CARD).pack(pady=30)
            return
        max_value = float(totals.max()) if not totals.empty else 1
        for category, value in totals.head(7).items():
            row = tk.Frame(body, bg=CARD)
            row.pack(fill="x", pady=6)
            color = CATEGORY_COLORS.get(category, BLUE)
            tk.Label(row, text=category, font=("Segoe UI", 8, "bold"), fg=TEXT, bg=CARD).pack(side="left")
            tk.Label(row, text=f"₹{value:,.0f}", font=("Segoe UI", 8, "bold"), fg=color, bg=CARD).pack(side="right")
            track = tk.Canvas(body, height=8, bg=CARD, highlightthickness=0)
            track.pack(fill="x", pady=(2, 0))
            track.update_idletasks()
            width = max(track.winfo_width(), 220)
            track.create_rectangle(0, 1, width, 7, fill="#EEF2F6", outline="")
            fill_w = width * (float(value) / max_value)
            track.create_rectangle(0, 1, fill_w, 7, fill=color, outline="")

    def _dashboard_budget(self, panel, month):
        body = tk.Frame(panel, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        total_budget = sum(b.limit for b in self.db.get_budgets().values())
        spent = self.analytics.month_total(month)
        remaining = total_budget - spent
        used = 0 if total_budget <= 0 else spent / total_budget * 100

        circle = tk.Canvas(body, width=150, height=150, bg=CARD, highlightthickness=0)
        circle.pack(pady=(2, 3))
        circle.create_oval(20, 20, 130, 130, outline="#ECF0F4", width=13)
        extent = min(359, max(0, used) * 3.6)
        color = GREEN if used < 80 else GOLD if used < 100 else RED
        circle.create_arc(20, 20, 130, 130, start=90, extent=-extent, style="arc", outline=color, width=13)
        circle.create_text(75, 65, text=f"{used:.0f}%", font=("Segoe UI", 18, "bold"), fill=TEXT)
        circle.create_text(75, 88, text="used", font=("Segoe UI", 8), fill=MUTED)

        tk.Label(body, text=f"₹{spent:,.0f} spent  •  ₹{remaining:,.0f} remaining", font=("Segoe UI", 9, "bold"), fg=TEXT, bg=CARD).pack()
        status = "Within Budget" if used < 80 else "Near Limit" if used < 100 else "Over Budget"
        status_color = GREEN if status == "Within Budget" else GOLD if status == "Near Limit" else RED
        tk.Label(body, text=status.upper(), font=("Segoe UI", 8, "bold"), fg=status_color, bg=CARD).pack(pady=(3, 8))

        budgets = self.db.get_budgets()
        totals = self.analytics.category_totals(month)
        ranked = totals.sort_values(ascending=False).index.tolist() if not totals.empty else []
        for category in ranked[:4]:
            budget = budgets.get(category, Budget(category, DEFAULT_BUDGETS.get(category, 1000))).limit
            spent_cat = float(totals.get(category, 0))
            accent = CATEGORY_COLORS.get(category, BLUE)
            self._progress_row(body, category, spent_cat, budget, accent)

        tk.Button(body, text="Open Budget →", command=lambda: self.show_page("Budget"), bg=SOFT_BLUE, fg=BLUE,
                  relief="flat", bd=0, font=("Segoe UI", 8, "bold"), padx=10, pady=7, cursor="hand2").pack(anchor="w", pady=(8, 0))

    def _fill_recent_table(self, parent, transactions):
        body = tk.Frame(parent, bg=CARD)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        columns = ("date", "category", "amount", "description")
        tree = ttk.Treeview(body, columns=columns, show="headings", height=7)
        tree.heading("date", text="DATE")
        tree.heading("category", text="CATEGORY")
        tree.heading("amount", text="AMOUNT")
        tree.heading("description", text="DESCRIPTION")
        tree.column("date", width=105, anchor="center")
        tree.column("category", width=120, anchor="center")
        tree.column("amount", width=105, anchor="e")
        tree.column("description", width=360, anchor="w")
        for t in reversed(transactions[-8:]):
            tree.insert("", "end", values=(t.date, t.category, f"₹{t.amount:,.0f}", t.description))
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

    def _fill_insights(self, parent, month):
        body = tk.Frame(parent, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        totals = self.analytics.category_totals(month)
        if totals.empty:
            text = "• Add expenses to start generating insights.\n\n• Use Analytics to visualize your spending.\n\n• Set budgets for each category from the Budget page."
        else:
            top = str(totals.index[0])
            second = str(totals.index[1]) if len(totals) > 1 else "-"
            top_value = float(totals.iloc[0])
            total = float(totals.sum())
            share = 0 if total == 0 else top_value / total * 100
            text = (
                f"• {top} is your highest-spending category this month.\n\n"
                f"• It accounts for about {share:.0f}% of monthly spending.\n\n"
                f"• {second} is your next major category.\n\n"
                f"• Use the Analytics page to compare trends over time."
            )
        tk.Label(body, text=text, font=("Segoe UI", 9), fg=TEXT, bg=CARD, justify="left", wraplength=360).pack(anchor="w", pady=6)

    # ========================================================
    # TRANSACTIONS
    # ========================================================
    def _show_transactions(self):
        tx = self.analytics.transactions
        months = ["All"] + self.analytics.month_list()

        top = tk.Frame(self.content, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        top.pack(fill="x", pady=(0, 12))
        tk.Label(top, text="SEARCH", font=("Segoe UI", 8, "bold"), fg=MUTED, bg=CARD).pack(side="left", padx=(16, 6), pady=12)
        search_var = tk.StringVar()
        search = tk.Entry(top, textvariable=search_var, width=28, font=("Segoe UI", 9), bg="#F7F9FC", fg=TEXT, relief="solid", bd=1)
        search.pack(side="left", pady=12, ipady=5)

        tk.Label(top, text="MONTH", font=("Segoe UI", 8, "bold"), fg=MUTED, bg=CARD).pack(side="left", padx=(18, 6))
        month_var = tk.StringVar(value="All")
        month_combo = ttk.Combobox(top, values=months, textvariable=month_var, state="readonly", width=12)
        month_combo.pack(side="left")
        tk.Label(top, text="CATEGORY", font=("Segoe UI", 8, "bold"), fg=MUTED, bg=CARD).pack(side="left", padx=(18, 6))
        cat_var = tk.StringVar(value="All")
        cat_combo = ttk.Combobox(top, values=["All"] + CATEGORIES, textvariable=cat_var, state="readonly", width=15)
        cat_combo.pack(side="left")

        result_label = tk.Label(top, text="", font=("Segoe UI", 8, "bold"), fg=BLUE, bg=CARD)
        result_label.pack(side="right", padx=16)

        panel = self._panel(self.content, "Transaction Ledger", "Filter the dataset or use the actions to manage records")
        panel.pack(fill="both", expand=True)
        tools = tk.Frame(panel, bg=CARD)
        tools.pack(fill="x", padx=16, pady=(0, 10))
        for text, command, color, fg in [
            ("＋ Add Expense", self.open_add_expense, TEAL, "white"),
            ("⇩ Import CSV", self.import_csv, NAVY_2, "white"),
            ("⇧ Export CSV", self.export_csv, SOFT_BLUE, BLUE),
        ]:
            tk.Button(tools, text=text, command=command, bg=color, fg=fg, relief="flat", bd=0,
                      font=("Segoe UI", 9, "bold"), padx=11, pady=7, cursor="hand2").pack(side="left", padx=(0, 6))

        body = tk.Frame(panel, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        columns = ("date", "category", "amount", "description")
        tree = ttk.Treeview(body, columns=columns, show="headings")
        for col, heading in zip(columns, ["DATE", "CATEGORY", "AMOUNT (₹)", "DESCRIPTION"]):
            tree.heading(col, text=heading)
        tree.column("date", width=120, anchor="center")
        tree.column("category", width=150, anchor="center")
        tree.column("amount", width=130, anchor="e")
        tree.column("description", width=650, anchor="w")
        yscroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        def refresh_table(*_):
            tree.delete(*tree.get_children())
            query = search_var.get().strip().lower()
            chosen_month = month_var.get()
            chosen_category = cat_var.get()
            shown = 0
            for t in reversed(tx):
                if chosen_month != "All" and not t.date.startswith(chosen_month):
                    continue
                if chosen_category != "All" and t.category != chosen_category:
                    continue
                haystack = f"{t.date} {t.category} {t.description}".lower()
                if query and query not in haystack:
                    continue
                tree.insert("", "end", values=(t.date, t.category, f"{t.amount:,.2f}", t.description))
                shown += 1
            result_label.config(text=f"{shown:,} matching records")

        search_var.trace_add("write", refresh_table)
        month_combo.bind("<<ComboboxSelected>>", refresh_table)
        cat_combo.bind("<<ComboboxSelected>>", refresh_table)
        refresh_table()

    # ========================================================
    # ANALYTICS
    # ========================================================
    def _show_analytics(self):
        """Build the analytics page once; tabs and month selector redraw only the chart."""
        toolbar = tk.Frame(self.content, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x", pady=(0, 12))

        left = tk.Frame(toolbar, bg=CARD)
        left.pack(side="left", padx=14, pady=12)
        tk.Label(
            left, text="VISUALIZATION", font=("Segoe UI", 8, "bold"),
            fg=MUTED, bg=CARD
        ).pack(anchor="w", pady=(0, 7))

        self.analytics_tab_buttons = {}
        tabs = tk.Frame(left, bg=CARD)
        tabs.pack(anchor="w")
        for mode in ["Monthly Trend", "Daily Trend", "Category Breakdown"]:
            btn = tk.Button(
                tabs,
                text=mode,
                command=lambda m=mode: self._set_analytics_mode(m),
                relief="flat", bd=0, cursor="hand2",
                font=("Segoe UI", 9, "bold"), padx=13, pady=7,
            )
            btn.pack(side="left", padx=(0, 6))
            self.analytics_tab_buttons[mode] = btn

        right = tk.Frame(toolbar, bg=CARD)
        right.pack(side="right", padx=18, pady=12)

        tk.Label(
            right, text="MONTH", font=("Segoe UI", 8, "bold"),
            fg=MUTED, bg=CARD
        ).pack(side="left", padx=(0, 8))

        months = self.analytics.month_list()
        month_options = ["All"] + months if months else ["All"]
        if self.selected_analytics_month not in month_options:
            self.selected_analytics_month = "All"

        self.analysis_month_var = tk.StringVar(value=self.selected_analytics_month)
        self.analysis_month_combo = ttk.Combobox(
            right,
            values=month_options,
            textvariable=self.analysis_month_var,
            state="readonly",
            width=16,
            justify="center",
            style="Analytics.TCombobox",
        )
        self.analysis_month_combo.pack(side="left")
        self.analysis_month_combo.bind("<<ComboboxSelected>>", self._analysis_month_changed)

        self.analysis_month_hint = tk.Label(
            right,
            text=f"  Showing: {self.selected_analytics_month}",
            font=("Segoe UI", 8), fg=MUTED, bg=CARD
        )
        self.analysis_month_hint.pack(side="left")

        # Summary chips
        chips = tk.Frame(self.content, bg=BG)
        chips.pack(fill="x", pady=(0, 10))
        month = self.selected_analytics_month
        self.analytics_chip_widgets = []
        initial_month = None if self.analytics_mode == "Monthly Trend" or month == "All" else month
        initial_total = self.analytics.total_spending() if initial_month is None else self.analytics.month_total(initial_month)
        initial_count = len(self.analytics.transactions) if initial_month is None else self.analytics.month_transaction_count(initial_month)
        initial_top = self.analytics.top_category(None) if initial_month is None else self.analytics.top_category(initial_month)
        vals = [
            ("TOTAL SPENDING" if initial_month is None else "MONTH TOTAL", f"₹{initial_total:,.0f}", BLUE),
            ("TRANSACTIONS", f"{initial_count:,}", TEAL),
            ("TOP CATEGORY", initial_top, PURPLE),
        ]
        for i, (title, value, color) in enumerate(vals):
            chips.grid_columnconfigure(i, weight=1)
            card = tk.Frame(chips, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 5, 5 if i < 2 else 0))
            tk.Label(card, text=title, font=("Segoe UI", 7, "bold"), fg=MUTED, bg=CARD).pack(anchor="w", padx=12, pady=(8, 0))
            tk.Label(card, text=value, font=("Segoe UI", 13, "bold"), fg=color, bg=CARD).pack(anchor="w", padx=12, pady=(2, 8))

        chart_panel = self._panel(
            self.content,
            "Spending Visualization",
            "Use All for complete history, or choose a month for focused analysis"
        )
        chart_panel.pack(fill="both", expand=True)
        self.chart_box = tk.Frame(chart_panel, bg=CARD)
        self.chart_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._update_analytics_tab_styles()
        self._update_analytics_month_control()
        self._draw_analytics_chart()

    def _update_analytics_tab_styles(self):
        for mode, button in self.analytics_tab_buttons.items():
            active = mode == self.analytics_mode
            button.config(
                bg=NAVY_2 if active else "#EEF2F7",
                fg="white" if active else TEXT,
                activebackground=NAVY_2 if active else "#E2E8F0",
                activeforeground="white" if active else TEXT,
            )

    def _update_analytics_month_control(self):
        """Show month filtering only for charts where it has a purpose.

        Monthly Trend always represents the complete month-by-month history,
        so there is no reason to offer a month selector on that tab.
        Daily Trend and Category Breakdown can be filtered to a single month
        or kept on All.
        """
        if self.analytics_mode == "Monthly Trend":
            # Monthly trend always uses every available month.
            self.analysis_month_combo.pack_forget()
            self.analysis_month_hint.config(text="  All months", fg=BLUE)
        else:
            self.analysis_month_combo.pack(side="left")
            self.analysis_month_combo.config(state="readonly")
            if self.selected_analytics_month == "All":
                self.analysis_month_hint.config(text="  Showing: All months", fg=MUTED)
            else:
                self.analysis_month_hint.config(text=f"  Showing: {self.selected_analytics_month}", fg=MUTED)

    def _set_analytics_mode(self, mode):
        self.analytics_mode = mode
        self._update_analytics_tab_styles()
        self._update_analytics_month_control()
        self._refresh_analytics_summary()
        self._draw_analytics_chart()

    def _analysis_month_changed(self, _event=None):
        # Monthly Trend does not use a month filter. This guard also keeps the
        # method safe if the combobox generates an event while the tab changes.
        if self.analytics_mode == "Monthly Trend":
            return

        value = self.analysis_month_var.get()
        if value:
            self.selected_analytics_month = value
        if self.selected_analytics_month == "All":
            self.analysis_month_hint.config(text="  Showing: All months", fg=MUTED)
        else:
            self.analysis_month_hint.config(text=f"  Showing: {self.selected_analytics_month}", fg=MUTED)
        self._refresh_analytics_summary()
        self._draw_analytics_chart()

    def _refresh_analytics_summary(self):
        """Refresh the analytics summary chips for the active visualization."""
        if not hasattr(self, "content"):
            return
        children = self.content.winfo_children()
        if len(children) < 2:
            return
        chips = children[1]

        # Monthly Trend is always an all-history view. For the other two
        # visualizations, respect the selected month or All.
        use_all_history = (
            self.analytics_mode == "Monthly Trend"
            or self.selected_analytics_month == "All"
        )
        month = None if use_all_history else self.selected_analytics_month

        if month is None:
            total = self.analytics.total_spending()
            count = len(self.analytics.transactions)
            top = self.analytics.top_category(None)
            total_label = "TOTAL SPENDING"
        else:
            total = self.analytics.month_total(month)
            count = self.analytics.month_transaction_count(month)
            top = self.analytics.top_category(month)
            total_label = "MONTH TOTAL"

        values = [f"₹{total:,.0f}", f"{count:,}", top]
        titles = [total_label, "TRANSACTIONS", "TOP CATEGORY"]

        cards = [w for w in chips.winfo_children() if isinstance(w, tk.Frame)]
        cards.sort(key=lambda w: int(w.grid_info().get("column", 0)))
        for card, title, value in zip(cards, titles, values):
            labels = [w for w in card.winfo_children() if isinstance(w, tk.Label)]
            if len(labels) >= 2:
                labels[0].config(text=title)
                labels[1].config(text=value)
    def _draw_analytics_chart(self):
        # Keep references to the Matplotlib objects; this prevents the embedded
        # figure from disappearing after the method returns.
        if hasattr(self, "analytics_canvas") and self.analytics_canvas is not None:
            try:
                self.analytics_canvas.get_tk_widget().destroy()
            except tk.TclError:
                pass
            self.analytics_canvas = None
        if hasattr(self, "analytics_figure") and self.analytics_figure is not None:
            try:
                plt.close(self.analytics_figure)
            except Exception:
                pass
            self.analytics_figure = None

        for widget in self.chart_box.winfo_children():
            widget.destroy()

        fig, ax = plt.subplots(figsize=(11.2, 5.0), dpi=100)
        self.analytics_figure = fig
        fig.patch.set_facecolor(CARD)
        ax.set_facecolor(CARD)

        if self.analytics_mode == "Monthly Trend":
            data = self.analytics.monthly_totals()
            if data.empty:
                self._empty_chart(ax, "No data available")
            else:
                x = np.arange(len(data))
                y = data.values
                ax.plot(x, y, marker="o", markersize=4, linewidth=2.5, color=BLUE)
                ax.fill_between(x, y, 0, color=SKY, alpha=0.15)
                ax.set_xticks(x)
                ax.set_xticklabels(data.index, rotation=45, ha="right", fontsize=8)
                ax.set_ylabel("Spending (₹)", fontsize=9, color=MUTED)
                ax.set_title("Monthly Spending Trend", loc="left", fontsize=13, fontweight="bold", color=TEXT, pad=10)

        elif self.analytics_mode == "Daily Trend":
            month = None if self.selected_analytics_month == "All" else self.selected_analytics_month
            data = self.analytics.daily_totals(month)
            if data.empty:
                self._empty_chart(ax, "No spending data available")
            else:
                # Use a real date axis instead of creating hundreds of text labels.
                # This is much faster for the 730-day dataset and keeps the graph readable.
                dates = pd.to_datetime(data.index)
                y = data.to_numpy(dtype=float)
                ax.plot(dates, y, color=TEAL, linewidth=1.8)
                ax.fill_between(dates, y, 0, color=TEAL, alpha=0.08)

                if len(data) <= 31:
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
                    ax.set_xlabel(f"Days in {self.selected_analytics_month}", fontsize=9, color=MUTED)
                else:
                    # For All months, show monthly labels only. The underlying
                    # line still contains every daily record.
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, len(data) // 365)))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
                    ax.set_xlabel("Date", fontsize=9, color=MUTED)

                ax.tick_params(axis="x", labelsize=8, rotation=35, colors=MUTED)
                ax.tick_params(axis="y", labelsize=8, colors=MUTED)
                ax.set_ylabel("Spending (₹)", fontsize=9, color=MUTED)
                title_scope = "All Months" if self.selected_analytics_month == "All" else self.selected_analytics_month
                ax.set_title(f"Daily Spending — {title_scope}", loc="left", fontsize=13, fontweight="bold", color=TEXT, pad=10)

        else:
            month = None if self.selected_analytics_month == "All" else self.selected_analytics_month
            data = self.analytics.category_totals(month)
            if data.empty:
                self._empty_chart(ax, "No category data available")
            else:
                labels = data.index.tolist()
                values = data.values
                colors = [CATEGORY_COLORS.get(label, BLUE) for label in labels]
                ax.pie(
                    values, labels=labels, colors=colors, startangle=90,
                    autopct="%1.0f%%", pctdistance=0.78,
                    wedgeprops={"width": 0.42, "edgecolor": CARD},
                    textprops={"fontsize": 8}
                )
                title_scope = "All Months" if self.selected_analytics_month == "All" else self.selected_analytics_month
                ax.set_title(
                    f"Category Breakdown — {title_scope}",
                    loc="left", fontsize=13, fontweight="bold", color=TEXT, pad=10
                )

        self._style_axes(ax)
        fig.tight_layout(pad=2)
        self.analytics_canvas = FigureCanvasTkAgg(fig, master=self.chart_box)
        widget = self.analytics_canvas.get_tk_widget()
        widget.configure(bg=CARD, highlightthickness=0, bd=0)
        widget.pack(fill="both", expand=True)
        self.analytics_canvas.draw()
        self.analytics_canvas.flush_events()

    @staticmethod
    def _style_axes(ax):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(BORDER)
        ax.spines["bottom"].set_color(BORDER)
        ax.tick_params(axis="x", colors=MUTED, length=0)
        ax.tick_params(axis="y", colors=MUTED, labelsize=8)
        ax.grid(axis="y", color="#E9EEF4", linewidth=0.8, alpha=0.8)
        ax.set_axisbelow(True)

    @staticmethod
    def _empty_chart(ax, text):
        ax.text(0.5, 0.5, text, ha="center", va="center", color=MUTED, fontsize=12)
        ax.axis("off")

    # ========================================================
    # BUDGET PAGE
    # ========================================================
    def _show_budget(self):
        months = self.analytics.month_list() or ["-"]
        if self.selected_budget_month not in months:
            self.selected_budget_month = months[-1]

        toolbar = tk.Frame(self.content, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        toolbar.pack(fill="x", pady=(0, 12))
        tk.Label(toolbar, text="MONTH", font=("Segoe UI", 8, "bold"), fg=MUTED, bg=CARD).pack(side="left", padx=(16, 7), pady=12)
        self.budget_month_var = tk.StringVar(value=self.selected_budget_month)
        month_combo = ttk.Combobox(toolbar, values=months, textvariable=self.budget_month_var, state="readonly", width=12)
        month_combo.pack(side="left", pady=12)
        month_combo.bind("<<ComboboxSelected>>", self._budget_month_changed)

        tk.Label(toolbar, text="CATEGORY", font=("Segoe UI", 8, "bold"), fg=MUTED, bg=CARD).pack(side="left", padx=(25, 7))
        self.budget_category_var = tk.StringVar(value="Food")
        category_combo = ttk.Combobox(toolbar, values=CATEGORIES, textvariable=self.budget_category_var, state="readonly", width=16)
        category_combo.pack(side="left")
        category_combo.bind("<<ComboboxSelected>>", self._load_selected_budget_value)

        tk.Label(toolbar, text="LIMIT (₹)", font=("Segoe UI", 8, "bold"), fg=MUTED, bg=CARD).pack(side="left", padx=(18, 7))
        self.budget_limit_entry = tk.Entry(toolbar, width=12, font=("Segoe UI", 9), bg="#F7F9FC", fg=TEXT, relief="solid", bd=1)
        self.budget_limit_entry.pack(side="left", ipady=5)
        tk.Button(toolbar, text="Save Budget", command=self.save_budget_from_page, bg=NAVY_2, fg="white", relief="flat", bd=0,
                  font=("Segoe UI", 9, "bold"), padx=11, pady=7, cursor="hand2").pack(side="left", padx=9)
        self._load_selected_budget_value()

        month_total = self.analytics.month_total(self.selected_budget_month)
        total_budget = sum(b.limit for b in self.db.get_budgets().values())
        remaining = total_budget - month_total
        used = 0 if total_budget == 0 else month_total / total_budget * 100
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x", pady=(0, 12))
        for i in range(3):
            cards.grid_columnconfigure(i, weight=1)
        MetricCard(cards, "MONTHLY LIMIT", f"₹{total_budget:,.0f}", "Combined category budgets", BLUE, "◈").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        MetricCard(cards, "MONTH SPENDING", f"₹{month_total:,.0f}", self.selected_budget_month, TEAL, "↗").grid(row=0, column=1, sticky="ew", padx=5)
        MetricCard(cards, "REMAINING", f"₹{remaining:,.0f}", f"{used:.0f}% used", GREEN if remaining >= 0 else RED, "✓" if remaining >= 0 else "!").grid(row=0, column=2, sticky="ew", padx=(5, 0))

        panel = self._panel(self.content, "Budget Status", f"Category-wise comparison for {self.selected_budget_month}")
        panel.pack(fill="both", expand=True)
        body = tk.Frame(panel, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        columns = ("category", "budget", "spent", "used", "status")
        tree = ttk.Treeview(body, columns=columns, show="headings")
        for col, heading in zip(columns, ["CATEGORY", "BUDGET (₹)", "SPENT (₹)", "USED", "STATUS"]):
            tree.heading(col, text=heading)
        tree.column("category", width=200, anchor="w")
        tree.column("budget", width=160, anchor="e")
        tree.column("spent", width=160, anchor="e")
        tree.column("used", width=130, anchor="center")
        tree.column("status", width=190, anchor="center")
        budgets = self.db.get_budgets()
        totals = self.analytics.category_totals(self.selected_budget_month)
        for category in CATEGORIES:
            budget = budgets.get(category, Budget(category, DEFAULT_BUDGETS.get(category, 1000))).limit
            spent = float(totals.get(category, 0.0))
            status = Budget(category, budget).status(spent)
            used_pct = 0 if budget <= 0 else spent / budget * 100
            tree.insert("", "end", values=(category, f"₹{budget:,.0f}", f"₹{spent:,.0f}", f"{used_pct:.0f}%", status))
        sb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _budget_month_changed(self, _event=None):
        self.selected_budget_month = self.budget_month_var.get()
        self._show_budget()

    def _load_selected_budget_value(self, _event=None):
        category = self.budget_category_var.get()
        budget = self.db.get_budgets().get(category)
        self.budget_limit_entry.delete(0, "end")
        self.budget_limit_entry.insert(0, str(int(budget.limit if budget else DEFAULT_BUDGETS.get(category, 1000))))

    def save_budget_from_page(self):
        category = self.budget_category_var.get()
        try:
            amount = float(self.budget_limit_entry.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Budget", "Enter a positive numeric monthly budget.")
            return
        self.db.save_budget(category, amount)
        self._show_budget()
        messagebox.showinfo("Budget Updated", f"{category} monthly budget set to ₹{amount:,.0f}.")

    # ========================================================
    # REPORTS PAGE
    # ========================================================
    def _show_reports(self):
        months = self.analytics.month_list() or ["-"]
        if self.selected_report_month not in months:
            self.selected_report_month = months[-1]

        topbar = tk.Frame(self.content, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        topbar.pack(fill="x", pady=(0, 12))
        tk.Label(topbar, text="REPORT MONTH", font=("Segoe UI", 8, "bold"), fg=MUTED, bg=CARD).pack(side="left", padx=(16, 7), pady=12)
        self.report_month_var = tk.StringVar(value=self.selected_report_month)
        combo = ttk.Combobox(topbar, values=months, textvariable=self.report_month_var, state="readonly", width=12)
        combo.pack(side="left", pady=12)
        combo.bind("<<ComboboxSelected>>", self._report_month_changed)
        tk.Button(topbar, text="Export Current Month", command=self.export_current_month, bg=NAVY_2, fg="white", relief="flat", bd=0,
                  font=("Segoe UI", 9, "bold"), padx=12, pady=7, cursor="hand2").pack(side="right", padx=16)

        month = self.selected_report_month
        total = self.analytics.month_total(month)
        count = self.analytics.month_transaction_count(month)
        avg = total / count if count else 0
        top_category = self.analytics.top_category(month)

        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x", pady=(0, 12))
        for i in range(4):
            cards.grid_columnconfigure(i, weight=1)
        MetricCard(cards, "MONTH TOTAL", f"₹{total:,.0f}", month, BLUE, "₹").grid(row=0, column=0, sticky="ew", padx=(0, 5))
        MetricCard(cards, "TRANSACTIONS", f"{count:,}", "Recorded this month", TEAL, "≡").grid(row=0, column=1, sticky="ew", padx=5)
        MetricCard(cards, "AVERAGE", f"₹{avg:,.0f}", "Average transaction", PURPLE, "≈").grid(row=0, column=2, sticky="ew", padx=5)
        MetricCard(cards, "TOP CATEGORY", top_category, "Highest spending category", GOLD, "★").grid(row=0, column=3, sticky="ew", padx=(5, 0))

        report_panel = self._panel(self.content, "Monthly Report", "A simple summary built from your transaction data")
        report_panel.pack(fill="both", expand=True)
        body = tk.Frame(report_panel, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        tk.Label(body, text=f"Expense Summary — {month}", font=("Segoe UI", 15, "bold"), fg=TEXT, bg=CARD).pack(anchor="w", pady=(8, 12))

        totals = self.analytics.category_totals(month)
        if totals.empty:
            tk.Label(body, text="No transactions available for this month.", font=("Segoe UI", 9), fg=MUTED, bg=CARD).pack(anchor="w")
        else:
            max_value = float(totals.max())
            for category, amount in totals.items():
                color = CATEGORY_COLORS.get(category, BLUE)
                row = tk.Frame(body, bg=CARD)
                row.pack(fill="x", pady=5)
                tk.Label(row, text=category, font=("Segoe UI", 9, "bold"), fg=TEXT, bg=CARD, width=18, anchor="w").pack(side="left")
                bar = tk.Canvas(row, height=12, bg=CARD, highlightthickness=0)
                bar.pack(side="left", fill="x", expand=True, padx=8)
                bar.update_idletasks()
                width = max(bar.winfo_width(), 300)
                bar.create_rectangle(0, 3, width, 9, fill="#EEF2F6", outline="")
                bar.create_rectangle(0, 3, width * float(amount / max_value), 9, fill=color, outline="")
                tk.Label(row, text=f"₹{amount:,.0f}", font=("Segoe UI", 9, "bold"), fg=color, bg=CARD, width=12, anchor="e").pack(side="right")

    def _report_month_changed(self, _event=None):
        self.selected_report_month = self.report_month_var.get()
        self._show_reports()

    def export_current_month(self):
        month = self.selected_report_month
        frame = self.analytics.month_df(month)
        if frame.empty:
            messagebox.showinfo("Export", "No transactions available for the selected month.")
            return
        path = filedialog.asksaveasfilename(title="Save Monthly Report", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        frame[["date", "category", "amount", "description"]].to_csv(path, index=False)
        messagebox.showinfo("Report Exported", f"Saved {len(frame):,} transactions from {month}.")

    # ========================================================
    # DATA ACTIONS
    # ========================================================
    def open_add_expense(self):
        win = tk.Toplevel(self)
        win.title("Add Expense")
        win.geometry("460x475")
        win.resizable(False, False)
        win.configure(bg=CARD)
        win.transient(self)
        win.grab_set()

        hero = tk.Frame(win, bg=NAVY_2)
        hero.pack(fill="x")
        tk.Label(hero, text="ADD NEW EXPENSE", font=("Segoe UI", 8, "bold"), fg="#A7DDE3", bg=NAVY_2).pack(anchor="w", padx=24, pady=(17, 2))
        tk.Label(hero, text="Keep your spending records up to date", font=("Segoe UI", 16, "bold"), fg="white", bg=NAVY_2).pack(anchor="w", padx=24, pady=(0, 16))

        form = tk.Frame(win, bg=CARD)
        form.pack(fill="both", expand=True, padx=26, pady=10)

        def entry_field(label, default=""):
            tk.Label(form, text=label, font=("Segoe UI", 9, "bold"), fg=TEXT, bg=CARD).pack(anchor="w", pady=(7, 4))
            entry = tk.Entry(form, font=("Segoe UI", 10), bg="#F7F9FC", fg=TEXT, relief="solid", bd=1)
            if default:
                entry.insert(0, default)
            entry.pack(fill="x", ipady=7)
            return entry

        date_entry = entry_field("Date (YYYY-MM-DD)", datetime.now().strftime(DATE_FORMAT))
        tk.Label(form, text="Category", font=("Segoe UI", 9, "bold"), fg=TEXT, bg=CARD).pack(anchor="w", pady=(9, 4))
        category_combo = ttk.Combobox(form, values=CATEGORIES, state="readonly", font=("Segoe UI", 10))
        category_combo.set("Food")
        category_combo.pack(fill="x", ipady=5)
        amount_entry = entry_field("Amount (₹)")
        desc_entry = entry_field("Short Description")

        def save():
            date = date_entry.get().strip()
            category = category_combo.get().strip()
            desc = desc_entry.get().strip()
            try:
                amount = float(amount_entry.get())
                if amount <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Amount", "Enter a positive numeric amount.", parent=win)
                return
            if not Transaction.valid_date(date):
                messagebox.showerror("Invalid Date", "Use the format YYYY-MM-DD.", parent=win)
                return
            self.db.add_transaction(Transaction(date, category, amount, desc))
            win.destroy()
            self.show_page(self.current_page)

        tk.Button(win, text="Save Expense", command=save, bg=TEAL, fg="white", relief="flat", bd=0,
                  font=("Segoe UI", 10, "bold"), padx=20, pady=9, cursor="hand2").pack(pady=15)

    def _read_csv_transactions(self, path):
        df = pd.read_csv(path)
        required = {"date", "category", "amount", "description"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError("CSV must contain: date, category, amount, description")
        transactions = []
        invalid_rows = 0
        for row in df.itertuples(index=False):
            date = str(row.date).strip()
            category = str(row.category).strip()
            description = str(row.description).strip()
            try:
                amount = float(row.amount)
            except (ValueError, TypeError):
                invalid_rows += 1
                continue
            if not Transaction.valid_date(date) or amount <= 0:
                invalid_rows += 1
                continue
            if category not in CATEGORIES:
                category = "Other"
            transactions.append(Transaction(date, category, amount, description))
        return transactions, invalid_rows

    def import_csv(self):
        path = filedialog.askopenfilename(title="Select Expense CSV", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            transactions, invalid = self._read_csv_transactions(path)
            if not transactions:
                raise ValueError("No valid transaction rows were found in the CSV file.")
            self.db.replace_transactions(transactions)
            self.show_page(self.current_page)
            messagebox.showinfo("Import Complete", f"Loaded {len(transactions):,} transactions.\nInvalid rows skipped: {invalid:,}")
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc))

    def load_demo_data(self):
        path = DEMO_FILE
        if not path.exists():
            fallback = BASE_DIR / "expense_30_days.csv"
            if fallback.exists():
                path = fallback
        if not path.exists():
            messagebox.showwarning("Demo Data Missing", "Place expense_730_days.csv in the same folder as this Python file.")
            return
        try:
            transactions, invalid = self._read_csv_transactions(path)
            if not transactions:
                raise ValueError("The demo CSV contains no valid data.")
            self.db.replace_transactions(transactions)
            self.show_page(self.current_page)
            messagebox.showinfo("Data Loaded", f"Loaded {len(transactions):,} demo transactions.\nInvalid rows skipped: {invalid:,}")
        except Exception as exc:
            messagebox.showerror("Demo Data Error", str(exc))

    def export_csv(self):
        transactions = self.db.get_transactions()
        if not transactions:
            messagebox.showinfo("Export", "There are no transactions to export.")
            return
        path = filedialog.asksaveasfilename(title="Save Expense CSV", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["date", "category", "amount", "description"])
            for transaction in TransactionIterator(transactions):
                writer.writerow(transaction.to_tuple())
        messagebox.showinfo("Export Complete", f"Exported {len(transactions):,} transactions successfully.")


if __name__ == "__main__":
    app = ExpenseApp()
    app.mainloop()
