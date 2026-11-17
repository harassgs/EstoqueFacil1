import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
DATABASE = os.path.join(os.path.dirname(__file__), "estoque.db")

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        category TEXT NOT NULL DEFAULT '',
        quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL REFERENCES products(id),
        kind TEXT NOT NULL CHECK(kind IN ('entrada','saida')),
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        note TEXT DEFAULT '',
        user_id INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    if not conn.execute("SELECT id FROM users LIMIT 1").fetchone():
        conn.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",
                     ("admin", generate_password_hash("admin123")))
    conn.commit()
    conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Usuário ou senha inválidos.", "error")
    return render_template("login.html")

@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    conn = db()
    stats = conn.execute("""
      SELECT COUNT(*) AS products,
             COALESCE(SUM(quantity),0) AS units,
             SUM(CASE WHEN quantity <= 5 THEN 1 ELSE 0 END) AS low
      FROM products
    """).fetchone()
    movements = conn.execute("""
      SELECT m.*, p.name AS product_name, u.username
      FROM movements m JOIN products p ON p.id=m.product_id
      LEFT JOIN users u ON u.id=m.user_id
      ORDER BY m.id DESC LIMIT 8
    """).fetchall()
    return render_template("dashboard.html", stats=stats, movements=movements)

@app.route("/produtos", methods=["GET", "POST"])
@login_required
def products():
    conn = db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip()
        category = request.form.get("category", "").strip()
        if not name or not code:
            flash("Nome e código são obrigatórios.", "error")
        else:
            try:
                conn.execute("INSERT INTO products(name,code,category) VALUES(?,?,?)",
                             (name, code, category))
                conn.commit()
                flash("Produto cadastrado com sucesso.", "success")
                return redirect(url_for("products"))
            except sqlite3.IntegrityError:
                flash("Já existe um produto com esse código.", "error")
    items = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    return render_template("products.html", products=items)

@app.route("/movimentacoes", methods=["GET", "POST"])
@login_required
def movements():
    conn = db()
    if request.method == "POST":
        try:
            product_id = int(request.form.get("product_id", ""))
            quantity = int(request.form.get("quantity", ""))
            kind = request.form.get("kind")
            note = request.form.get("note", "").strip()
            if quantity <= 0 or kind not in ("entrada", "saida"):
                raise ValueError()
            conn.execute("BEGIN IMMEDIATE")
            product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if product is None:
                raise ValueError()
            if kind == "saida" and product["quantity"] < quantity:
                conn.rollback()
                flash("Estoque insuficiente para essa saída.", "error")
                return redirect(url_for("movements"))
            delta = quantity if kind == "entrada" else -quantity
            conn.execute("UPDATE products SET quantity=quantity+? WHERE id=?", (delta, product_id))
            conn.execute("""INSERT INTO movements(product_id,kind,quantity,note,user_id)
                            VALUES(?,?,?,?,?)""",
                         (product_id, kind, quantity, note, session["user_id"]))
            conn.commit()
            flash("Movimentação registrada.", "success")
            return redirect(url_for("movements"))
        except (ValueError, TypeError):
            conn.rollback()
            flash("Confira o produto e a quantidade informados.", "error")
    product_list = conn.execute("SELECT id,name,code,quantity FROM products ORDER BY name").fetchall()
    history = conn.execute("""
      SELECT m.*, p.name AS product_name, u.username
      FROM movements m JOIN products p ON p.id=m.product_id
      LEFT JOIN users u ON u.id=m.user_id
      ORDER BY m.id DESC LIMIT 100
    """).fetchall()
    return render_template("movements.html", products=product_list, movements=history)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
