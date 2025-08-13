import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
#Replacing google sheets with a proper SQL Database
import sys
import os
from collections import defaultdict
from fractions import Fraction
import re

DB_CONNECTION_STRING = "postgresql://postgres:5ozM6i7!n6Y&9Teg@db.dsobueksiixyhnrtgtby.supabase.co:5432/postgres"
recipe_id_map = {}
def get_db_connection():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        return(conn)
    except psycopg2.OperationalError as e:
        messagebox.showerror("Database Error", f"Could not connect to the database.\nPlease check your connection string and internet.\n\nError: {e}")
        return None
# --- GLOBAL DATA AND CONFIG ---
MAX_INGREDIENTS = 20
MEASUREMENT_OPTIONS = [
    " ", "Cup(s)", "Tsp(s)", "Tbsp(s)", "Oz", "Lb(s)", "g", "Kg",
    "mL", "L", "Each", "Pinch", "Dash"
]
# ======================================================================
# RECIPE LOGGER WINDOW
# ======================================================================
def open_recipe_logger_window():
    logger_window = tk.Toplevel(window)
    logger_window.title("Recipe Logger")
    logger_window.geometry("525x620")
    main_frame = tk.Frame(logger_window)
    main_frame.pack(fill=tk.BOTH, expand=1)
    my_canvas = tk.Canvas(main_frame)
    my_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
    my_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=my_canvas.yview)
    my_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    my_canvas.configure(yscrollcommand=my_scrollbar.set)
    my_canvas.bind('<Configure>', lambda e: my_canvas.configure(scrollregion = my_canvas.bbox("all")))
    second_frame = tk.Frame(my_canvas)
    my_canvas.create_window((0,0), window=second_frame, anchor="nw")
    def on_mouse_wheel(event):
        my_canvas.yview_scroll(-1 * int(event.delta / 120), "units")
    my_canvas.bind_all("<MouseWheel>", on_mouse_wheel)
    ingredient_widgets=[]
    def add_ingredient_row():
        row_index = len(ingredient_widgets) + 1 # +1 to account for the header row
        qty_entry = tk.Entry(ingredients_frame, width=8)
        unit_combo = ttk.Combobox(ingredients_frame, width=10, values=MEASUREMENT_OPTIONS)
        name_var = tk.StringVar()
        name_entry = tk.Entry(ingredients_frame, width=30, textvariable=name_var)
        qty_entry.grid(row=row_index, column=0, padx=2, pady=2)
        unit_combo.grid(row=row_index, column=1, padx=2, pady=2)
        name_entry.grid(row=row_index, column=2, padx=2, pady=2)
        widget_set = {'quantity': qty_entry, 'unit': unit_combo, 'name': name_entry, 'name_var': name_var}
        ingredient_widgets.append(widget_set)
        name_var.trace_add("write", lambda name, index, mode, var=name_var: on_last_ingredient_typed(var))

        def on_last_ingredient_typed(triggered_var):
            """Callback function that adds a new row when the last one is typed in."""
            if triggered_var is ingredient_widgets[-1]['name_var'] and triggered_var.get() != "":
                triggered_var.trace_remove("write", triggered_var.trace_info()[0][1])
                add_ingredient_row()
    def submit_recipe():
        recipe_title = title_entry.get()
        author_name = author_entry.get()
        if not recipe_title or not author_name:
            messagebox.showerror("Error", "Please fill in both the Title and Author fields.", parent=logger_window)
            return
        ingredients_to_add = []
        for widget_set in ingredient_widgets:
            name = widget_set['name'].get()
            if name:
                quantity = widget_set['quantity'].get()
                unit = widget_set['unit'].get()
                ingredients_to_add.append({'quantity': quantity, 'unit': unit, 'name': name})
        instructions = instructions_text.get("1.0", tk.END).strip()
        conn = get_db_connection()
        if not conn: return
        
        try:
            with conn.cursor() as cur:
                sql_insert_recipe = "INSERT INTO recipes (title, author, instructions) VALUES (%s, %s, %s) RETURNING id;"
                cur.execute(sql_insert_recipe, (recipe_title, author_name, instructions))
                
                new_recipe_id = cur.fetchone()[0]
                
                sql_insert_ingredient = "INSERT INTO ingredients (recipe_id, quantity, unit, name) VALUES (%s, %s, %s, %s);"
                for ing in ingredients_to_add:
                    cur.execute(sql_insert_ingredient, (new_recipe_id, ing['quantity'], ing['unit'], ing['name']))
                conn.commit()
                messagebox.showinfo("Success", "Recipe submitted successfully!", parent=logger_window)
                logger_window.destroy()
                refresh_recipe_list()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", f"An error occurred: {e}", parent=logger_window)
        finally:
            if conn:
                conn.close()

    def clear_fields():
        """Clears all input fields in the logger window."""
        title_entry.delete(0, tk.END)
        author_entry.delete(0, tk.END)
        for widget_set in ingredient_widgets:
            widget_set['quantity'].destroy()
            widget_set['unit'].destroy()
            widget_set['name'].destroy()
        ingredient_widgets.clear()
        for _ in range(5):
            add_ingredient_row()
        instructions_text.delete("1.0", tk.END)
    title_frame = tk.Frame(second_frame, padx=10, pady=5)
    title_frame.pack(fill='x')
    tk.Label(title_frame, text="Recipe Title:").pack(side='left')
    title_entry = tk.Entry(title_frame)
    title_entry.pack(side='left', expand=True, fill='x')
    author_frame = tk.Frame(second_frame, padx=10, pady=2)
    author_frame.pack(fill='x')
    tk.Label(author_frame, text="Submitter:", width=15, anchor='w').pack(side='left')
    author_entry = tk.Entry(author_frame)
    author_entry.pack(side='left', expand=True, fill='x')

    ingredients_frame = tk.Frame(second_frame, padx=10, pady=5)
    ingredients_frame.pack()
    ingredient_entries = []
    tk.Label(ingredients_frame, text="Qty").grid(row=0, column=0)
    tk.Label(ingredients_frame, text="Unit").grid(row=0, column=1)
    tk.Label(ingredients_frame, text="Ingredient Name").grid(row=0, column=2)

    for _ in range(5):
        add_ingredient_row()

    instructions_frame = tk.Frame(second_frame, padx=10, pady=5)
    instructions_frame.pack(fill='x')
    tk.Label(instructions_frame, text="Instructions:").pack()
    instructions_text = tk.Text(instructions_frame, width=60, height=10, wrap='word')
    instructions_text.pack(expand=True, fill='both')

    button_frame = tk.Frame(second_frame, pady=10)
    button_frame.pack()
    tk.Button(button_frame, text="Submit Recipe", command=submit_recipe).pack(side='left', padx=5)
    tk.Button(button_frame, text="Clear Fields", command=clear_fields).pack(side='left', padx=5)
# ======================================================================
# GROCERY GENERATOR WINDOW
# ======================================================================
def open_grocery_generator_window():
    messagebox.showinfo("Coming Soon", "The Grocery Generator needs to be updated to work with the new SQL database!")
# ======================================================================
# MAIN RECIPE HUB APPLICATION
# ======================================================================

def delete_selected_recipe():
    """Finds the selected recipe by its index, asks for confirmation, and deletes it."""
    selected_indices = recipe_listbox.curselection()
    if not selected_indices:
        messagebox.showwarning("No Selection", "Please select a recipe from the list to delete.")
        return
    recipe_title = recipe_listbox.get(selected_indices[0])
    recipe_id = recipe_id_map.get(recipe_title)
    if not recipe_id: return

    if messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete '{recipe_title}'?"):
        conn = get_db_connection()
        if not conn: return
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM recipes WHERE id = %s;", (recipe_id,))
                conn.commit()
            messagebox.showinfo("Success", f"'{recipe_title}' has been deleted.")
            refresh_recipe_list()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", f"Could not delete recipe: {e}")
        finally:
            conn.close()


def refresh_recipe_list():
    """Fetches all recipe titles from the database and populates the listbox."""
    global recipe_id_map
    recipe_id_map.clear()
    recipe_listbox.delete(0, tk.END)

    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM recipes ORDER BY title ASC;")
            all_recipes = cur.fetchall()
            
            for recipe in all_recipes:
                recipe_id, recipe_title = recipe
                recipe_id_map[recipe_title] = recipe_id
                recipe_listbox.insert(tk.END, recipe_title)

    except Exception as e:
        messagebox.showerror("Database Error", f"Could not fetch recipes: {e}")
    finally:
        conn.close()
        
def on_recipe_select(event):
    """Fetches and displays the full details for the selected recipe."""
    selected_indices = recipe_listbox.curselection()
    if not selected_indices: return
    
    recipe_title = recipe_listbox.get(selected_indices[0])
    recipe_id = recipe_id_map.get(recipe_title)
    if not recipe_id: return

    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT author, instructions FROM recipes WHERE id = %s;", (recipe_id,))
            recipe_details = cur.fetchone()
            author_name, instructions = recipe_details
            cur.execute("SELECT quantity, unit, name FROM ingredients WHERE recipe_id = %s;", (recipe_id,))
            ingredients_list = cur.fetchall()
            ingredients_display = "\n".join(f"- {qty} {unit} {name}".strip() for qty, unit, name in ingredients_list)
            ingredients_text.config(state='normal'); instructions_text.config(state='normal')
            ingredients_text.delete('1.0', tk.END); instructions_text.delete('1.0', tk.END)
            ingredients_text.insert(tk.END, ingredients_display); instructions_text.insert(tk.END, instructions)
            ingredients_text.config(state='disabled'); instructions_text.config(state='disabled')
            author_label.config(text=f"Submitted by: {author_name}")
    except Exception as e:
        messagebox.showerror("Database Error", f"Could not fetch recipe details: {e}")
    finally:
        conn.close()

# --- MAIN WINDOW GUI SETUP ---
window = tk.Tk()
window.title("Recipe Hub")
window.geometry("800x600")

# --- Top bar for controls ---
top_frame = tk.Frame(window, padx=10, pady=5)
top_frame.pack(side='top', fill='x')

# Buttons on the left
tk.Button(top_frame, text="📝 Add New Recipe", command=open_recipe_logger_window).pack(side='left')
tk.Button(top_frame, text="🛒 Create Grocery List", command=open_grocery_generator_window).pack(side='left', padx=5)
tk.Button(top_frame, text="🔄 Refresh List", command=refresh_recipe_list).pack(side='left')

# --- NEW: Delete button on the right ---

# --- Main Layout Frames ---
list_frame = tk.Frame(window, padx=10, pady=10)
list_frame.pack(side='left', fill='y')
display_frame = tk.Frame(window, padx=10, pady=10)
display_frame.pack(side='right', expand=True, fill='both')

# --- Recipe List (Left Side) ---
tk.Label(list_frame, text="Select a Recipe", font=("Helvetica", 14)).pack(pady=5)
recipe_listbox = tk.Listbox(list_frame, width=30, font=("Helvetica", 12))
recipe_listbox.pack(expand=True, fill='y')
recipe_listbox.bind('<<ListboxSelect>>', on_recipe_select)

# --- Recipe Display (Right Side) ---
tk.Label(display_frame, text="Ingredients", font=("Helvetica", 14)).pack()
ingredients_text = tk.Text(display_frame, height=10, font=("Helvetica", 11), wrap='word', state='disabled')
ingredients_text.pack(expand=True, fill='both', pady=5)
tk.Label(display_frame, text="Instructions", font=("Helvetica", 14)).pack()
instructions_text = tk.Text(display_frame, height=15, font=("Helvetica", 11), wrap='word', state='disabled')
instructions_text.pack(expand=True, fill='both', pady=5)

# --- Author Display Label ---
author_label = tk.Label(display_frame, text="", font=("Helvetica", 10, "italic"), anchor='e')
author_label.pack(fill='x', side='bottom', padx=5)

# --- Load initial data and run the app ---
refresh_recipe_list()
window.mainloop()
