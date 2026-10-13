# Personal Expense Analytics & Budget Management System

A Python-based desktop application designed to track daily expenses, manage monthly budgets, analyze spending habits, and display financial information through an interactive dashboard.

Built using Python, Tkinter, Pandas, NumPy, Matplotlib, and SQLite, this project combines object-oriented programming, data analysis, database management, and data visualization.

## ✨ Features

- **Interactive Dashboard** – Displays total expenses, average spending, highest expenses, and budget summaries.
- **Expense Tracking** – Add, search, filter, and manage daily transactions.
- **Budget Management** – Set monthly spending limits for different categories.
- **Expense Analysis** – View daily trends, monthly trends, and category-wise spending.
- **Smart Insights** – Identify high-spending categories and understand spending patterns.
- **CSV Import and Export** – Import transaction data and export expense records.
- **SQLite Database** – Store transaction and budget information locally.
- **Data Visualization** – Generate charts using Matplotlib.
- **Desktop Interface** – Simple graphical interface developed using Tkinter.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python 3 | Core programming language |
| Tkinter | Graphical user interface |
| Pandas | Data processing and analysis |
| NumPy | Numerical calculations |
| Matplotlib | Charts and visualizations |
| SQLite3 | Database management |
| CSV Module | Importing and exporting data |

## 🏗️ System Architecture

The application consists of four main layers:

1. **User Interface:** Tkinter dashboard, forms, and navigation.
2. **Application Logic:** Expense management, budget calculations, and validation.
3. **Analytics and Visualization:** Pandas, NumPy, and Matplotlib.
4. **Storage:** SQLite database and CSV files.

### Application Workflow

```text
Manual Entry / CSV Import
          |
          v
   Transaction Processing
          |
          v
    SQLite Database
          |
          v
    Pandas DataFrame
          |
          v
     Expense Analysis
          |
          v
   Charts and Dashboard
          |
          v
  Budget Status and Insights
```

## 🧠 Python Concepts Implemented

- **Object-Oriented Programming:** Classes, objects, and encapsulation.
- **Inheritance:** Reusable components based on Tkinter classes.
- **Functional Programming:** `map()`, `lambda`, and `reduce()`.
- **Custom Iterators:** `__iter__()` and `__next__()`.
- **Data Analysis:** Pandas DataFrames and `groupby()`.
- **Numerical Computing:** NumPy functions for totals and averages.
- **Database Connectivity:** SQLite operations using Python.
- **File Handling:** CSV import and export.
- **Data Visualization:** Charts integrated into the Tkinter interface.

## 📂 Project Structure

```text
Personal-Expense-Analytics/
│
├── expense_budget_dashboard.py
├── sample_transactions.csv
├── expense_730_days.csv
├── requirements.txt
├── README.md
└── .gitignore
```

### File Descriptions

- `expense_budget_dashboard.py` – Main application source code.
- `sample_transactions.csv` – Sample transaction records.
- `expense_730_days.csv` – Sample dataset covering approximately two years.
- `requirements.txt` – Required Python libraries.
- `README.md` – Project documentation.
- `.gitignore` – Specifies files Git should not track.

The SQLite database, `expenses.db`, is created automatically when the application initializes.

## ⚙️ Installation and Setup

### Prerequisites

- Python 3.10 or later
- Git
- Visual Studio Code, PyCharm, or another Python IDE

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/Personal-Expense-Analytics.git
```

Replace `YOUR-USERNAME` with your GitHub username.

### Step 2: Navigate to the Project Directory

```bash
cd Personal-Expense-Analytics
```

### Step 3: Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### Step 4: Install Dependencies

Create a `requirements.txt` file containing:

```text
pandas
numpy
matplotlib
```

Install the required libraries:

```bash
pip install -r requirements.txt
```

### Step 5: Run the Application

```bash
python expense_budget_dashboard.py
```

The desktop application should open in a new window.

**Note:** Tkinter and SQLite3 are generally included with Python installations.

## 📊 Sample Dataset

The application supports CSV files containing transaction records.

```csv
date,category,amount,description
2026-01-01,Food,250,Breakfast
2026-01-02,Transport,120,Bus fare
2026-01-03,Education,500,Books
2026-01-04,Entertainment,350,Movie
2026-01-05,Shopping,800,Clothing
```

### Supported Categories

- Food
- Transport
- Education
- Entertainment
- Utilities
- Shopping
- Rent
- Health
- Personal Care
- Other

Each transaction includes a date, category, amount, and description.

## 💵 Default Monthly Budgets

| Category | Monthly Budget |
|---|---:|
| Food | ₹5,000 |
| Transport | ₹2,500 |
| Education | ₹2,500 |
| Entertainment | ₹2,000 |
| Utilities | ₹1,800 |
| Shopping | ₹3,500 |
| Rent | ₹10,000 |
| Health | ₹2,000 |
| Personal Care | ₹1,500 |
| Other | ₹1,000 |
| **Total** | **₹31,800** |

Users can modify budget limits through the application.

## 🎯 Budget Status

| Status | Condition |
|---|---|
| Within Budget | Spending is below 80% of the budget limit. |
| Near Limit | Spending reaches at least 80% of the limit without exceeding it. |
| Over Budget | Spending exceeds the budget limit. |
| No Budget | No positive budget limit is configured. |

These indicators help users monitor their expenses and identify categories that require attention.

## 📈 Analytics and Visualization

The application provides the following analytical features:

- **Monthly Trend:** Tracks spending changes across months.
- **Daily Trend:** Displays expenses recorded on individual dates.
- **Category Breakdown:** Compares spending across categories.
- **Financial Summary:** Shows total, average, and largest expenses.
- **Budget Analysis:** Compares actual spending with budget limits.
- **Smart Insights:** Highlights the highest-spending category.

## 🗄️ Database Design

The application uses SQLite to maintain two primary tables.

### Transactions Table

Stores individual expense records.

| Column | Description |
|---|---|
| `id` | Unique transaction identifier |
| `date` | Transaction date |
| `category` | Expense category |
| `amount` | Amount spent |
| `description` | Transaction details |

### Budgets Table

Stores monthly budget information.

| Column | Description |
|---|---|
| `category` | Expense category |
| `limit_amount` | Monthly budget limit |

SQLite provides persistent local storage without requiring a separate database server.

## 🎓 Project Objectives

1. **Record:** Maintain organized records of daily expenses.
2. **Analyze:** Calculate spending summaries by category, date, and month.
3. **Control:** Compare actual expenses against budget limits.
4. **Visualize:** Present spending patterns through dashboards and charts.

### Course Outcomes

- **CO1:** Apply object-oriented programming to develop modular and reusable Python applications.
- **CO4:** Use data processing and visualization libraries to analyze and present information.
- **CO5:** Develop applications integrating databases and user interfaces to solve practical problems.

## 🔐 Data Privacy

- Expense information is stored locally in an SQLite database.
- The application does not require an external database server.
- CSV files support importing and exporting transaction records.
- Personal financial records should not be uploaded to a public repository.

**Important:** Do not upload your personal `expenses.db` database or other sensitive financial information to GitHub.

## 🔮 Future Enhancements

Possible improvements include:

- Automatic expense categorization.
- Recurring expense detection.
- Budget limit notifications.
- PDF and Excel report generation.
- Savings goal tracking.
- Advanced financial analytics.
- Optional cloud synchronization.

These are proposed enhancements and may require additional development.

## 👥 Project Team

This project was developed as an academic micro-project by:

- Baby Rao Metta
- Harshita Chhabra
- Rajasree G
- B Lakshmi Priya

## 📌 Project Information

| Detail | Description |
|---|---|
| Project Title | Personal Expense Analytics & Budget Management System |
| Project Type | Python Desktop Application |
| Course | Advanced Python Programming |
| Programming Language | Python |
| User Interface | Tkinter |
| Database | SQLite |
| Data Analysis | Pandas and NumPy |
| Visualization | Matplotlib |

## 🤝 Contributing

Suggestions and improvements are welcome.

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Test the application.
5. Submit a pull request.

## 📜 License

This project was developed for academic purposes. An appropriate open-source license can be added if the project is distributed publicly.

## ⭐ Support

If you find this project useful, consider giving the repository a star on GitHub.

Your feedback and suggestions are welcome!

---

**Track your expenses. Understand your spending. Manage your budget better.**
