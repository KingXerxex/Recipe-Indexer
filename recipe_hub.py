import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
#Replacing google sheets with a proper SQL Database
import sys
import os
from collections import defaultdict
from fractions import Fraction
import re

DB_CONNECTION_STRING = "postgresql://postgres:[PASSWORD]@db.dsobueksiixyhnrtgtby.supabase.co:5432/postgres"
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
    """
    Opens a new Toplevel window containing the grocery list generator UI and logic.
    """
    generator_window = tk.Toplevel(window)
    generator_window.title("Grocery List Generator")
    generator_window.geometry("1400x500")

    # This list of counters is now local to this window
    recipe_counters = []

    # --- Helper functions for the generator ---
    def format_fraction(frac):
        """Nicely formats a Fraction object into a string like '1 1/2'."""
        if frac is None: return ""
        if frac.denominator == 1:
            return str(frac.numerator)
        if frac.numerator > frac.denominator:
            whole = frac.numerator // frac.denominator
            rem_num = frac.numerator % frac.denominator
            if rem_num == 0:
                return str(whole)
            return f"{whole} {rem_num}/{frac.denominator}"
        return f"{frac.numerator}/{frac.denominator}"

    def convert_to_fraction(s):
        """Converts a string like '1 1/2' or '3/4' or '2' to a Fraction object."""
        s = s.strip()
        if not s: return Fraction(0)
        try:
            if ' ' in s:
                parts = s.split()
                return int(parts[0]) + Fraction(parts[1])
            return Fraction(s)
        except (ValueError, ZeroDivisionError):
            return Fraction(0)

    def parse_ingredient(ingredient_str):
        """Parses an ingredient string like '2 Cup(s) Flour' into (qty, unit, name)."""
        ingredient_str = ingredient_str.strip()
        # Use a version of the units list without the blank space
        valid_units = [u for u in MEASUREMENT_OPTIONS if u.strip()]
        # Sort units by length, longest first, to match "Tbsp(s)" before "Tsp(s)"
        sorted_units = sorted(valid_units, key=len, reverse=True)
        
        found_unit = ""
        # Create a flexible regex to find the unit, even if it's missing the '(s)'
        for unit in sorted_units:
            # Prepare a regex pattern that ignores the '(s)' for matching purposes
            pattern_base = re.escape(unit.replace('(s)', ''))
            pattern = r'\b' + pattern_base + r'(\(s\))?\b'
            
            match = re.search(pattern, ingredient_str, re.IGNORECASE)
            if match:
                found_unit = match.group(0) # The actual unit found, e.g. "Cup" or "Cup(s)"
                break
        
        if found_unit:
            parts = re.split(r'\b' + re.escape(found_unit) + r'\b', ingredient_str, maxsplit=1, flags=re.IGNORECASE)
            quantity_str = parts[0].strip()
            name_str = parts[1].strip()
            return (quantity_str, found_unit, name_str)
        else:
            # If no unit, assume the first word is quantity if it looks like one
            parts = ingredient_str.split(' ', 1)
            if len(parts) > 1 and re.match(r'^[0-9./\s]+$', parts[0]):
                return (parts[0].strip(), "Each", parts[1].strip())
            else:
                return ("1", "Each", ingredient_str)

    def generate_list():
        selected_recipes = []
        for var, title in recipe_counters:
            if var.get() > 0:
                selected_recipes.append({'title': title, 'count': var.get()})
        
        if not selected_recipes:
            messagebox.showwarning("Warning", "Please add at least one recipe.", parent=generator_window)
            return

        grocery_list = defaultdict(lambda: defaultdict(Fraction))
        for item in selected_recipes:
            for recipe in all_recipes_data:
                if recipe and recipe[0] == item['title']:
                    multiplier = item['count']
                    # Use the correct slice to get all possible ingredient columns
                    all_possible_ingredients = recipe[1:1 + MAX_INGREDIENTS]
                    for ing_str in all_possible_ingredients:
                        if ing_str.strip():
                            qty_str, unit, name = parse_ingredient(ing_str)
                            quantity = convert_to_fraction(qty_str) * multiplier
                            # Normalize name to be lowercase and singular for better grouping
                            name = name.lower().strip()
                            grocery_list[name][unit] += quantity
                    break
        
        # --- MODIFIED FORMATTING SECTION ---
        # Create a list of formatted strings to be sorted
        output_lines = []
        for name, amounts in grocery_list.items():
            for unit, total_quantity in amounts.items():
                if total_quantity > 0:
                    # Format the parts of the line
                    qty_str = format_fraction(total_quantity)
                    unit_str = unit if unit != "Each" else ""
                    # Capitalize the ingredient name for display
                    name_str = name.capitalize()
                    
                    # Add to a list of tuples for sorting: (name, qty, unit)
                    output_lines.append((name_str, qty_str, unit_str))
        
        # Sort the list alphabetically by the ingredient name (the first item in the tuple)
        output_lines.sort(key=lambda x: x[0])

        # Build the final display text with clean alignment
        display_text = ""
        for name_str, qty_str, unit_str in output_lines:
            # Use ljust to left-align the quantity in a fixed-width column
            # This creates the clean alignment you wanted
            aligned_qty = qty_str.ljust(8)
            display_text += f"{aligned_qty}{unit_str} {name_str}\n"

        # --- Display the list ---
        grocery_list_text.config(state='normal')
        grocery_list_text.delete('1.0', tk.END)
        grocery_list_text.insert(tk.END, display_text)
        grocery_list_text.config(state='disabled')

    # --- UI for the new generator window (Unchanged) ---
    left_frame = tk.Frame(generator_window, padx=10, pady=10)
    left_frame.pack(side='left', fill='y')
    right_frame = tk.Frame(generator_window, padx=10, pady=10)
    right_frame.pack(side='right', expand=True, fill='both')

    tk.Label(left_frame, text="Select Meals", font=("Helvetica", 12)).pack()
    canvas = tk.Canvas(left_frame)
    scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    generate_button = tk.Button(right_frame, text="Generate Grocery List", command=generate_list)
    generate_button.pack(pady=10)
    grocery_list_text = tk.Text(right_frame, wrap='word', state='disabled', font=("Courier", 11))
    grocery_list_text.pack(expand=True, fill='both')

    def decrease_count(var):
        if var.get() > 0: var.set(var.get() - 1)
    def increase_count(var):
        var.set(var.get() + 1)

    start_row = 1 if all_recipes_data and all_recipes_data[0][0].lower() in ["title", "recipe title"] else 0
    for row in all_recipes_data[start_row:]:
        if row:
            recipe_title = row[0]
            recipe_frame = ttk.Frame(scrollable_frame)
            recipe_frame.pack(fill='x', expand=True, pady=2)
            count_var = tk.IntVar(value=0)
            ttk.Label(recipe_frame, text=recipe_title).pack(side='left', expand=True, fill='x', padx=5)
            ttk.Button(recipe_frame, text="-", width=3, command=lambda v=count_var: decrease_count(v)).pack(side='left')
            ttk.Label(recipe_frame, textvariable=count_var, width=3, anchor='center').pack(side='left')
            ttk.Button(recipe_frame, text="+", width=3, command=lambda v=count_var: increase_count(v)).pack(side='left')
            recipe_counters.append((count_var, recipe_title))
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
