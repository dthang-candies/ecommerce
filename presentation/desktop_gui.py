import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np


class DesktopGUI:
    """
    Presentation Layer: Desktop GUI (Tkinter)
    Provides an interactive native desktop application interface.
    Follows: UI -> Application -> Data
    """

    def __init__(self, search_ui):
        self.search_ui = search_ui
        self.root = tk.Tk()
        self.root.title("Multimodal E-Commerce Search (Assignment 05/06)")
        self.root.geometry("880x620")
        self.root.minsize(750, 520)

        self.setup_ui()

    def setup_ui(self):
        # Header
        header_frame = ttk.Frame(self.root, padding=12)
        header_frame.pack(fill=tk.X)

        title_lbl = ttk.Label(
            header_frame,
            text="Multimodal E-Commerce Search System",
            font=("Helvetica", 16, "bold")
        )
        title_lbl.pack(anchor=tk.W)

        subtitle_lbl = ttk.Label(
            header_frame,
            text="Presentation Layer (Three-Layer Architecture: UI ➔ Application ➔ Data)",
            font=("Helvetica", 10),
            foreground="gray"
        )
        subtitle_lbl.pack(anchor=tk.W)

        # Mode Selection Frame
        mode_frame = ttk.LabelFrame(self.root, text="Select Search Mode (Use Case)", padding=10)
        mode_frame.pack(fill=tk.X, padx=12, pady=4)

        self.search_mode = tk.StringVar(value="text")
        modes = [
            ("Text / Keyword", "text"),
            ("Voice (Simulated STT)", "voice"),
            ("Image (Cosine Similarity)", "image"),
            ("Multimodal Fusion", "multimodal"),
            ("Search Order", "order")
        ]

        for text, val in modes:
            rb = ttk.Radiobutton(
                mode_frame,
                text=text,
                value=val,
                variable=self.search_mode,
                command=self.on_mode_change
            )
            rb.pack(side=tk.LEFT, padx=10)

        # Search Controls Frame
        input_frame = ttk.Frame(self.root, padding=12)
        input_frame.pack(fill=tk.X)

        self.input_label = ttk.Label(input_frame, text="Query Text:", font=("Helvetica", 10, "bold"))
        self.input_label.pack(side=tk.LEFT, padx=4)

        self.entry_query = ttk.Entry(input_frame, font=("Helvetica", 11))
        self.entry_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self.entry_query.insert(0, "black running shoes")
        self.entry_query.bind("<Return>", lambda e: self.perform_search())

        # Image preset dropdown (initially hidden/shown based on mode)
        self.img_preset_var = tk.StringVar(value="shoes")
        self.img_dropdown = ttk.Combobox(
            input_frame,
            textvariable=self.img_preset_var,
            values=["shoes", "running_shoes", "bag", "clothing", "watch"],
            state="readonly",
            width=14
        )

        self.btn_search = ttk.Button(input_frame, text="🔍 Search", command=self.perform_search)
        self.btn_search.pack(side=tk.LEFT, padx=4)

        self.btn_all = ttk.Button(input_frame, text="All Products", command=self.show_all_products)
        self.btn_all.pack(side=tk.LEFT, padx=4)

        # Results Notebook / Views
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Tab 1: Product Results
        self.prod_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.prod_tab, text="Product Results (View Product)")

        columns = ("id", "name", "category", "color", "price", "stock", "score")
        self.tree_products = ttk.Treeview(self.prod_tab, columns=columns, show="headings", selectmode="browse")

        self.tree_products.heading("id", text="ID")
        self.tree_products.heading("name", text="Product Name")
        self.tree_products.heading("category", text="Category")
        self.tree_products.heading("color", text="Color")
        self.tree_products.heading("price", text="Price ($)")
        self.tree_products.heading("stock", text="Stock")
        self.tree_products.heading("score", text="Score / Sim")

        self.tree_products.column("id", width=40, anchor=tk.CENTER)
        self.tree_products.column("name", width=230)
        self.tree_products.column("category", width=90)
        self.tree_products.column("color", width=80)
        self.tree_products.column("price", width=70, anchor=tk.E)
        self.tree_products.column("stock", width=60, anchor=tk.CENTER)
        self.tree_products.column("score", width=90, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(self.prod_tab, orient=tk.VERTICAL, command=self.tree_products.yview)
        self.tree_products.configure(yscrollcommand=tree_scroll.set)

        self.tree_products.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_products.bind("<Double-1>", self.on_product_double_click)

        # Tab 2: Orders View
        self.order_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.order_tab, text="Order Tracking (View Order)")

        self.order_display = tk.Text(self.order_tab, font=("Courier", 11), padx=12, pady=12)
        self.order_display.pack(fill=tk.BOTH, expand=True)

        # Status Bar
        self.status_var = tk.StringVar(value="Ready. Double click any product to view details.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=4)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.show_all_products()

    def on_mode_change(self):
        mode = self.search_mode.get()
        if mode == "image":
            self.input_label.config(text="Select Prototype:")
            self.entry_query.pack_forget()
            self.img_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        elif mode == "multimodal":
            self.input_label.config(text="Text + Image:")
            self.entry_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            self.img_dropdown.pack(side=tk.LEFT, padx=4)
        elif mode == "order":
            self.input_label.config(text="Order ID:")
            self.img_dropdown.pack_forget()
            self.entry_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            self.entry_query.delete(0, tk.END)
            self.entry_query.insert(0, "O001")
        else:
            self.input_label.config(text="Query Text:")
            self.img_dropdown.pack_forget()
            self.entry_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

    def perform_search(self):
        mode = self.search_mode.get()
        query = self.entry_query.get().strip()

        if mode == "text":
            results = self.search_ui.search_by_text(query, apply_ranking=True)
            self.populate_products(results, f"Text Search: '{query}'")
            self.notebook.select(self.prod_tab)

        elif mode == "voice":
            results = self.search_ui.search_by_voice(query, apply_ranking=True)
            self.populate_products(results, f"Voice Search (STT): '{query}'")
            self.notebook.select(self.prod_tab)

        elif mode == "image":
            prototype = self.img_preset_var.get()
            results = self.search_ui.search_by_image(prototype, apply_ranking=False)
            self.populate_products(results, f"Visual Similarity: '{prototype}'")
            self.notebook.select(self.prod_tab)

        elif mode == "multimodal":
            prototype = self.img_preset_var.get()
            results = self.search_ui.search_multimodal(text=query, image_input=prototype, apply_ranking=True)
            self.populate_products(results, f"Multimodal Fusion: '{query}' + '{prototype}'")
            self.notebook.select(self.prod_tab)

        elif mode == "order":
            order = self.search_ui.search_order(query)
            self.display_order_details(order, query)
            self.notebook.select(self.order_tab)

    def populate_products(self, results, title=""):
        for row in self.tree_products.get_children():
            self.tree_products.delete(row)

        for prod, score in results:
            self.tree_products.insert("", tk.END, values=(
                prod.get("id"),
                prod.get("name"),
                prod.get("category"),
                prod.get("color"),
                f"{prod.get('price')}",
                prod.get("stock"),
                f"{score}"
            ))

        self.status_var.set(f"{title} - Found {len(results)} items.")

    def show_all_products(self):
        prods = self.search_ui.search_service.repository.all_products()
        pairs = [(p, "-") for p in prods]
        self.populate_products(pairs, "Catalog: All Products")
        self.notebook.select(self.prod_tab)

    def display_order_details(self, order, order_id):
        self.order_display.delete("1.0", tk.END)
        if not order:
            self.order_display.insert(tk.END, f"❌ Order '{order_id}' was NOT found in the database.\n\nTry O001, O002, O003, or 20261001.")
            self.status_var.set(f"Order '{order_id}' not found.")
            return

        out = "="*50 + "\n"
        out += f"  ORDER DETAILS: #{order.get('order_id')}\n"
        out += "="*50 + "\n\n"
        out += f"Customer ID : {order.get('customer_id')}\n"
        out += f"Date        : {order.get('date', 'N/A')}\n"
        out += f"Status      : {order.get('status')}\n"
        out += f"Total       : ${order.get('total')}\n\n"
        out += "Items in Order:\n"
        for it in order.get("items", []):
            out += f"  - Product ID: #{it.get('product_id')} | Quantity: {it.get('quantity')} | Unit Price: ${it.get('price')}\n"
        self.order_display.insert(tk.END, out)
        self.status_var.set(f"Order #{order_id} loaded successfully.")

    def on_product_double_click(self, event):
        selected = self.tree_products.selection()
        if not selected:
            return
        item = self.tree_products.item(selected[0])
        prod_id = item["values"][0]
        prod = self.search_ui.search_service.repository.find_by_id(prod_id)
        if prod:
            msg = (
                f"Name: {prod.get('name')}\n"
                f"Category: {prod.get('category')} | Color: {prod.get('color')}\n"
                f"Price: ${prod.get('price')} | Stock: {prod.get('stock')}\n\n"
                f"Description:\n{prod.get('description')}\n\n"
                f"Vector Embedding:\n{prod.get('embedding')}"
            )
            messagebox.showinfo(f"Product #{prod_id} Details", msg)

    def run(self):
        self.root.mainloop()


def start_desktop_gui(search_ui):
    app = DesktopGUI(search_ui)
    app.run()
