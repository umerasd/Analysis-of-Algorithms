import random
import time
import tkinter as tk
from collections import deque


FONT = "Segoe UI"

BG = "#0f172a"
PANEL = "#1e293b"
CARD = "#334155"
TEXT = "#f1f5f9"
MUTED = "#94a3b8"
SHADOW = "#020617"

WALL = "#1e293b"
WALL_EDGE = "#2d3b52"
FLOOR = "#e2e8f0"
FLOOR_GRID = "#cbd5e1"

PLAYER = "#f97316"
GOAL = "#10b981"
CHASER = "#e11d48"
FRONTIER = "#facc15"
ACCENT = "#6366f1"
LEVEL_COLORS = ("#38bdf8", "#818cf8", "#f472b6")

BTN_NEW = "#6366f1"
BTN_HINT = "#f59e0b"
BTN_UNDO = "#0ea5e9"
BTN_OFF = "#475569"
BTN_RUN = "#10b981"
BTN_STEP = "#8b5cf6"
BTN_CLEAR = "#64748b"

LEVELS = {
    "Easy": {"size": 15, "chaser_ms": 650},
    "Medium": {"size": 21, "chaser_ms": 480},
    "Hard": {"size": 27, "chaser_ms": 360},
}
MAX_HINTS = 3
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def neighbors(grid, cell):
    r, c = cell
    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < len(grid) and 0 <= nc < len(grid) and grid[nr][nc] == 0:
            yield (nr, nc)


def bfs(grid, start, goal=None):
    queue = deque([start])
    dist = {start: 0}
    parent = {start: None}
    while queue:
        cell = queue.popleft()
        if cell == goal:
            break
        for nb in neighbors(grid, cell):
            if nb not in dist:
                dist[nb] = dist[cell] + 1
                parent[nb] = cell
                queue.append(nb)
    return dist, parent


def build_path(parent, goal):
    if goal not in parent:
        return []
    path = []
    while goal is not None:
        path.append(goal)
        goal = parent[goal]
    return path[::-1]


def shortest_path(grid, start, goal):
    _, parent = bfs(grid, start, goal)
    return build_path(parent, goal)


def bfs_steps(grid, start, goal):
    queue = deque([start])
    parent = {start: None}
    while queue:
        cell = queue.popleft()
        discovered = []
        if cell != goal:
            for nb in neighbors(grid, cell):
                if nb not in parent:
                    parent[nb] = cell
                    queue.append(nb)
                    discovered.append(nb)
        yield cell, discovered, len(queue), parent
        if cell == goal:
            return


def generate_maze(n):
    grid = [[1] * n for _ in range(n)]
    grid[1][1] = 0
    stack = [(1, 1)]
    while stack:
        r, c = stack[-1]
        options = [(dr, dc) for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
                   if 0 < r + dr < n - 1 and 0 < c + dc < n - 1 and grid[r + dr][c + dc] == 1]
        if options:
            dr, dc = random.choice(options)
            grid[r + dr // 2][c + dc // 2] = 0
            grid[r + dr][c + dc] = 0
            stack.append((r + dr, c + dc))
        else:
            stack.pop()

    for _ in range(n * n // 6):
        r, c = random.randrange(1, n - 1), random.randrange(1, n - 1)
        if grid[r][c] == 1:
            vertical = grid[r - 1][c] == 0 and grid[r + 1][c] == 0 and grid[r][c - 1] == 1 and grid[r][c + 1] == 1
            horizontal = grid[r][c - 1] == 0 and grid[r][c + 1] == 0 and grid[r - 1][c] == 1 and grid[r + 1][c] == 1
            if vertical or horizontal:
                grid[r][c] = 0
    return grid


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def level_color(t):
    a, b, c = LEVEL_COLORS
    return mix(a, b, t * 2) if t < 0.5 else mix(b, c, (t - 0.5) * 2)


class FlatButton(tk.Label):
    def __init__(self, parent, text, command, color=CARD, fg="#ffffff", **kw):
        super().__init__(parent, text=text, bg=color, fg=fg, font=(FONT, 11, "bold"),
                         padx=10, pady=10, cursor="hand2", relief="flat",
                         highlightthickness=2, highlightbackground=color, **kw)
        self.color, self.command = color, command
        self.bind("<Enter>", lambda e: self.config(bg=mix(self.color, "#ffffff", 0.18),
                                                   highlightbackground="#ffffff"))
        self.bind("<Leave>", lambda e: self.config(bg=self.color, highlightbackground=self.color))
        self.bind("<Button-1>", lambda e: self.command())

    def set_color(self, color):
        self.color = color
        self.config(bg=color, highlightbackground=color)


class MazeRunner:
    def __init__(self, root):
        self.root = root
        root.title("BFS Maze Runner")
        root.configure(bg=BG)
        try:
            root.state("zoomed")
        except tk.TclError:
            root.attributes("-fullscreen", True)
        root.bind("<F11>", lambda e: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
        root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))

        self.board = max(420, root.winfo_screenheight() - 190)
        self.difficulty = "Medium"
        self.best_scores = {name: None for name in LEVELS}
        self.chaser_on = False
        self.anim_job = None
        self.hint_job = None

        self.build_ui()
        root.bind("<Key>", self.on_key)
        self.new_game()
        self.timer_loop()
        self.chaser_loop()

    def build_ui(self):
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(expand=True)

        left = tk.Frame(wrap, bg=BG)
        left.grid(row=0, column=0, padx=(0, 24), sticky="n")

        self.status = tk.Label(left, font=(FONT, 13, "bold"), bg=BG, fg=TEXT, anchor="w")
        self.status.pack(fill="x")
        self.canvas = tk.Canvas(left, width=self.board, height=self.board, bg=WALL, highlightthickness=0)
        self.canvas.pack(pady=8)
        tk.Label(left, bg=BG, fg=MUTED, font=(FONT, 10),
                 text="Move: Arrows / WASD    Undo: Z    Hint: H    BFS: B run · N step · X clear    "
                      "Chaser: C    New: R    Fullscreen: F11").pack()

        side = tk.Frame(wrap, bg=PANEL, padx=20, pady=16)
        side.grid(row=0, column=1, sticky="ns")

        tk.Label(side, text="BFS Maze Runner", font=(FONT, 22, "bold"), bg=PANEL, fg=TEXT).pack(anchor="w")
        tk.Label(side, text="Beat the Breadth-First Search shortest path", font=(FONT, 10),
                 bg=PANEL, fg=MUTED).pack(anchor="w")

        self.section(side, "DIFFICULTY")
        self.diff_buttons = {}
        row = self.button_row(side)
        for i, name in enumerate(LEVELS):
            b = FlatButton(row, f"{name}  ({i + 1})", lambda n=name: self.set_difficulty(n), CARD)
            b.grid(row=0, column=i, sticky="ew", padx=3)
            self.diff_buttons[name] = b

        self.section(side, "GAME STATS")
        self.stats = self.card_grid(side, [("steps", "Steps"), ("target", "BFS Target"), ("time", "Time"),
                                           ("hints", "Hints Left"), ("undos", "Undos"), ("best", "Best Score")], 3)

        self.section(side, "GAME")
        row = self.button_row(side, cols=2)
        FlatButton(row, "New Maze  (R)", self.new_game, BTN_NEW).grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        FlatButton(row, "Hint  (H)", self.hint, BTN_HINT, fg=BG).grid(row=0, column=1, sticky="ew", padx=3, pady=3)
        FlatButton(row, "Undo  (Z)", self.undo, BTN_UNDO).grid(row=1, column=0, sticky="ew", padx=3, pady=3)
        self.chaser_btn = FlatButton(row, "Chaser: OFF  (C)", self.toggle_chaser, BTN_OFF)
        self.chaser_btn.grid(row=1, column=1, sticky="ew", padx=3, pady=3)

        self.section(side, "BFS VISUALIZER  (start → goal)")
        row = self.button_row(side)
        self.run_btn = FlatButton(row, "▶ Run  (B)", self.run_bfs, BTN_RUN)
        self.run_btn.grid(row=0, column=0, sticky="ew", padx=3)
        FlatButton(row, "Step  (N)", self.step_bfs, BTN_STEP).grid(row=0, column=1, sticky="ew", padx=3)
        FlatButton(row, "Clear  (X)", self.clear_bfs, BTN_CLEAR).grid(row=0, column=2, sticky="ew", padx=3)

        row = tk.Frame(side, bg=PANEL)
        row.pack(fill="x", pady=(10, 0))
        tk.Label(row, text="Speed", font=(FONT, 10), bg=PANEL, fg=MUTED).pack(side="left")
        self.speed = tk.Scale(row, from_=1, to=10, orient="horizontal", showvalue=0, bg=PANEL,
                              troughcolor=CARD, highlightthickness=0, bd=0, sliderrelief="flat",
                              activebackground=FRONTIER, width=14)
        self.speed.set(6)
        self.speed.pack(side="left", fill="x", expand=True, padx=8)

        self.info = self.card_grid(side, [("visited", "Visited"), ("queue", "Queue"),
                                          ("level", "Level"), ("path", "Path")], 4)

        self.section(side, "LEGEND")
        legend = tk.Frame(side, bg=PANEL)
        legend.pack(fill="x")
        items = [(PLAYER, "You"), (GOAL, "Goal / BFS path"), (CHASER, "Chaser"),
                 (FRONTIER, "In queue"), (LEVEL_COLORS[0], "Visited (near)"), (LEVEL_COLORS[2], "Visited (far)")]
        for i, (color, text) in enumerate(items):
            cell = tk.Frame(legend, bg=PANEL)
            cell.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 16))
            tk.Label(cell, text="■", fg=color, bg=PANEL, font=(FONT, 12)).pack(side="left")
            tk.Label(cell, text=text, fg=TEXT, bg=PANEL, font=(FONT, 10)).pack(side="left")

        self.complexity = tk.Label(side, font=(FONT, 10), bg=PANEL, fg=MUTED, justify="left", anchor="w")
        self.complexity.pack(fill="x", pady=(12, 0))

    def section(self, parent, title):
        tk.Label(parent, text=title, font=(FONT, 9, "bold"), bg=PANEL, fg=MUTED).pack(anchor="w", pady=(14, 5))

    def button_row(self, parent, cols=3):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x")
        for i in range(cols):
            row.columnconfigure(i, weight=1, uniform="btn")
        return row

    def card_grid(self, parent, items, cols):
        frame = tk.Frame(parent, bg=PANEL)
        frame.pack(fill="x", pady=(4, 0))
        values = {}
        for i, (key, title) in enumerate(items):
            card = tk.Frame(frame, bg=CARD, padx=10, pady=6)
            card.grid(row=i // cols, column=i % cols, sticky="ew", padx=3, pady=3)
            frame.columnconfigure(i % cols, weight=1, uniform="card")
            tk.Label(card, text=title, font=(FONT, 9), bg=CARD, fg=MUTED).pack(anchor="w")
            values[key] = tk.Label(card, text="-", font=(FONT, 15, "bold"), bg=CARD, fg=TEXT)
            values[key].pack(anchor="w")
        return values

    def say(self, text, color=TEXT):
        self.status.config(text=text, fg=color)

    def set_difficulty(self, name):
        self.difficulty = name
        self.new_game()

    def new_game(self):
        self.stop_animation()
        self.bfs_gen = None

        n = LEVELS[self.difficulty]["size"]
        self.n = n
        self.grid = generate_maze(n)
        self.start, self.goal = (1, 1), (n - 2, n - 2)

        self.level_of, _ = bfs(self.grid, self.start)
        self.max_level = max(self.level_of.values())
        self.target = len(shortest_path(self.grid, self.start, self.goal)) - 1

        self.player = self.start
        self.history = []
        self.trail = []
        self.undos = 0
        self.hints = MAX_HINTS
        self.start_time = self.end_time = None
        self.state = "playing"
        self.chaser = self.chaser_spawn()

        V = len(self.level_of)
        E = sum(len(list(neighbors(self.grid, cell))) for cell in self.level_of) // 2
        self.complexity.config(text=f"Maze graph: V = {V} cells, E = {E} edges\n"
                                    f"BFS time O(V + E)  ·  space O(V)")

        for name, b in self.diff_buttons.items():
            b.set_color(ACCENT if name == self.difficulty else CARD)

        self.draw_board()
        self.reset_info()
        self.update_stats()
        self.say(f"Reach the goal in {self.target} steps - that's the BFS shortest path!", TEXT)

    def chaser_spawn(self):
        corners = [(self.n - 2, 1), (1, self.n - 2)]
        return max(corners, key=lambda c: abs(c[0] - self.player[0]) + abs(c[1] - self.player[1]))

    def xy(self, cell):
        r, c = cell
        return self.off + c * self.cs + self.cs / 2, self.off + r * self.cs + self.cs / 2

    def draw_board(self):
        cv = self.canvas
        cv.delete("all")
        self.cs = self.board // self.n
        self.off = (self.board - self.cs * self.n) // 2
        self.floor = {}
        for r in range(self.n):
            for c in range(self.n):
                x, y = self.off + c * self.cs, self.off + r * self.cs
                if self.grid[r][c] == 0:
                    self.floor[(r, c)] = cv.create_rectangle(x, y, x + self.cs, y + self.cs,
                                                             fill=FLOOR, outline=FLOOR_GRID)
                else:
                    cv.create_rectangle(x, y, x + self.cs, y + self.cs, fill=WALL, outline=WALL_EDGE)

        sx, sy = self.xy(self.start)
        r = self.cs * 0.38
        cv.create_oval(sx - r, sy - r, sx + r, sy + r, outline=PLAYER, dash=(3, 2), width=2)

        gx, gy = self.xy(self.goal)
        for f, color in ((0.42, GOAL), (0.28, FLOOR), (0.15, GOAL)):
            r = self.cs * f
            cv.create_oval(gx - r, gy - r, gx + r, gy + r, fill=color, outline="", tags="goal")

        cv.create_oval(0, 0, 0, 0, fill=PLAYER, outline="#ffffff", width=2, tags="player")
        cv.create_oval(0, 0, 0, 0, fill=CHASER, outline="#ffffff", width=2, tags="chaser")
        self.place("player", self.player, 0.36)
        self.place("chaser", self.chaser, 0.34)
        cv.itemconfig("chaser", state="normal" if self.chaser_on else "hidden")

    def place(self, tag, cell, size):
        x, y = self.xy(cell)
        r = self.cs * size
        self.canvas.coords(tag, x - r, y - r, x + r, y + r)

    def draw_line(self, cells, color, tag, width=None, dash=None):
        self.canvas.delete(tag)
        if len(cells) < 2:
            return
        points = [p for cell in cells for p in self.xy(cell)]
        self.canvas.create_line(*points, fill=color, width=width or max(3, self.cs // 5),
                                capstyle="round", joinstyle="round", dash=dash, tags=tag)
        self.raise_tokens()

    def raise_tokens(self):
        for tag in ("trail", "bfs_path", "hint", "chase_line", "cursor", "goal", "player", "chaser", "overlay"):
            if self.canvas.find_withtag(tag):
                self.canvas.tag_raise(tag)

    def show_overlay(self, title, color, lines, stars=None):
        cv = self.canvas
        mid = self.board / 2
        w, h = 420, 260 if stars else 210
        x0, y0 = mid - w / 2, mid - h / 2
        cv.create_rectangle(x0 + 6, y0 + 6, x0 + w + 6, y0 + h + 6, fill=SHADOW, outline="", tags="overlay")
        cv.create_rectangle(x0, y0, x0 + w, y0 + h, fill=PANEL, outline=color, width=3, tags="overlay")
        y = y0 + 40
        cv.create_text(mid, y, text=title, fill=color, font=(FONT, 22, "bold"), tags="overlay")
        if stars is not None:
            y += 44
            cv.create_text(mid, y, text="★" * stars + "☆" * (3 - stars), fill=FRONTIER,
                           font=(FONT, 28), tags="overlay")
        y += 40
        for line in lines:
            cv.create_text(mid, y, text=line, fill=TEXT, font=(FONT, 11), tags="overlay")
            y += 24
        cv.create_text(mid, y0 + h - 20, text="Press R for a new maze", fill=MUTED,
                       font=(FONT, 9), tags="overlay")

    def on_key(self, e):
        k = e.keysym.lower()
        moves = {"up": (-1, 0), "w": (-1, 0), "down": (1, 0), "s": (1, 0),
                 "left": (0, -1), "a": (0, -1), "right": (0, 1), "d": (0, 1)}
        actions = {"z": self.undo, "h": self.hint, "b": self.run_bfs, "n": self.step_bfs,
                   "x": self.clear_bfs, "r": self.new_game, "c": self.toggle_chaser,
                   "1": lambda: self.set_difficulty("Easy"), "2": lambda: self.set_difficulty("Medium"),
                   "3": lambda: self.set_difficulty("Hard")}
        if k in moves:
            self.move(*moves[k])
        elif k in actions:
            actions[k]()

    def move(self, dr, dc):
        if self.state != "playing":
            return
        r, c = self.player[0] + dr, self.player[1] + dc
        if self.grid[r][c] == 1:
            return
        if self.start_time is None:
            self.start_time = time.time()

        x, y = self.xy(self.player)
        d = max(2, self.cs * 0.1)
        self.trail.append(self.canvas.create_oval(x - d, y - d, x + d, y + d, fill=PLAYER,
                                                  outline="", tags="trail"))
        self.history.append(self.player)
        self.player = (r, c)
        self.place("player", self.player, 0.36)
        self.raise_tokens()
        self.update_stats()

        if self.player == self.goal:
            self.win()
        elif self.chaser_on and self.player == self.chaser:
            self.lose()

    def undo(self):
        if self.state != "playing" or not self.history:
            return
        self.player = self.history.pop()
        self.canvas.delete(self.trail.pop())
        self.undos += 1
        self.place("player", self.player, 0.36)
        self.update_stats()

    def hint(self):
        if self.state != "playing":
            return
        if self.hints == 0:
            self.say("No hints left!", CHASER)
            return
        self.hints -= 1
        path = shortest_path(self.grid, self.player, self.goal)
        self.draw_line(path[:8], PLAYER, "hint", width=max(2, self.cs // 7), dash=(6, 4))
        self.say(f"Hint: BFS says the goal is {len(path) - 1} steps away from you. Follow the dashes!", BTN_HINT)
        if self.hint_job:
            self.root.after_cancel(self.hint_job)
        self.hint_job = self.root.after(2000, lambda: self.canvas.delete("hint"))
        self.update_stats()

    def toggle_chaser(self):
        self.chaser_on = not self.chaser_on
        self.chaser_btn.config(text="Chaser: ON  (C)" if self.chaser_on else "Chaser: OFF  (C)")
        self.chaser_btn.set_color(CHASER if self.chaser_on else BTN_OFF)
        self.canvas.delete("chase_line")
        if self.chaser_on and self.state == "playing":
            self.chaser = self.chaser_spawn()
            self.place("chaser", self.chaser, 0.34)
            self.say("Chaser ON - it uses BFS every move to find you. Run!", CHASER)
        self.canvas.itemconfig("chaser", state="normal" if self.chaser_on else "hidden")
        self.raise_tokens()

    def chaser_loop(self):
        if (self.chaser_on and self.state == "playing" and self.start_time is not None
                and self.anim_job is None):
            path = shortest_path(self.grid, self.chaser, self.player)
            if len(path) > 1:
                self.chaser = path[1]
                self.place("chaser", self.chaser, 0.34)
                self.draw_line(path[1:], CHASER, "chase_line", width=2, dash=(2, 4))
            if self.chaser == self.player:
                self.lose()
        self.root.after(LEVELS[self.difficulty]["chaser_ms"], self.chaser_loop)

    def win(self):
        self.state = "won"
        self.end_time = time.time()
        steps = len(self.history)
        hints_used = MAX_HINTS - self.hints
        efficiency = self.target / steps * 100
        score = max(0, round(1000 * self.target / steps) - 100 * hints_used - 25 * self.undos)
        if steps == self.target and hints_used == 0:
            stars = 3
        elif efficiency >= 75:
            stars = 2
        else:
            stars = 1

        best = self.best_scores[self.difficulty]
        new_best = best is None or score > best
        if new_best:
            self.best_scores[self.difficulty] = score
        self.update_stats()

        self.canvas.delete("chase_line")
        self.draw_line(shortest_path(self.grid, self.start, self.goal), GOAL, "bfs_path")
        title = "PERFECT RUN!" if steps == self.target else "Maze Complete!"
        self.show_overlay(title, GOAL, [
            f"Your steps: {steps}     BFS shortest: {self.target}",
            f"Efficiency: {efficiency:.0f}%     Time: {self.end_time - self.start_time:.1f}s",
            f"Score: {score}" + ("   (new best!)" if new_best else ""),
        ], stars)
        self.say("Green line = BFS shortest path. Orange dots = your path.", GOAL)

    def lose(self):
        self.state = "lost"
        self.end_time = time.time()
        self.show_overlay("CAUGHT!", CHASER, [
            "The chaser found you with BFS.",
            f"You were {len(shortest_path(self.grid, self.player, self.goal)) - 1} steps from the goal.",
        ])
        self.say("Caught by the BFS chaser! Press R to try again.", CHASER)

    def update_stats(self):
        s = self.stats
        steps = len(self.history)
        s["steps"].config(text=str(steps), fg=CHASER if steps > self.target else TEXT)
        s["target"].config(text=str(self.target), fg=GOAL)
        s["hints"].config(text=f"{self.hints}/{MAX_HINTS}")
        s["undos"].config(text=str(self.undos))
        best = self.best_scores[self.difficulty]
        s["best"].config(text="-" if best is None else str(best), fg=FRONTIER)

    def timer_loop(self):
        if self.start_time is None:
            self.stats["time"].config(text="0:00")
        else:
            secs = int((self.end_time or time.time()) - self.start_time)
            self.stats["time"].config(text=f"{secs // 60}:{secs % 60:02d}")
        self.root.after(250, self.timer_loop)

    def reset_info(self):
        for label in self.info.values():
            label.config(text="-", fg=TEXT)

    def stop_animation(self):
        if self.anim_job:
            self.root.after_cancel(self.anim_job)
        self.anim_job = None
        if hasattr(self, "run_btn"):
            self.run_btn.config(text="▶ Run  (B)")

    def clear_bfs(self):
        self.stop_animation()
        self.bfs_gen = None
        for item in self.floor.values():
            self.canvas.itemconfig(item, fill=FLOOR)
        if self.state == "playing":
            self.canvas.delete("bfs_path")
        self.canvas.delete("cursor")
        self.reset_info()

    def run_bfs(self):
        if self.anim_job:
            self.stop_animation()
            self.say("BFS paused. Press B to continue or N to step.", MUTED)
            return
        self.run_btn.config(text="❚❚ Pause  (B)")
        self.say("BFS explores level by level: every cell at distance d before any at d + 1.", LEVEL_COLORS[0])
        self.animate()

    def animate(self):
        if self.bfs_step_once():
            self.stop_animation()
            return
        delay = max(5, int(400 * 0.65 ** (self.speed.get() - 1)))
        self.anim_job = self.root.after(delay, self.animate)

    def step_bfs(self):
        self.stop_animation()
        self.bfs_step_once()

    def bfs_step_once(self):
        if self.bfs_gen is None:
            self.clear_bfs()
            self.bfs_gen = bfs_steps(self.grid, self.start, self.goal)
            self.visited_count = 0
        try:
            cell, discovered, queue_size, parent = next(self.bfs_gen)
        except StopIteration:
            self.bfs_gen = None
            return True

        self.visited_count += 1
        level = self.level_of[cell]
        self.canvas.itemconfig(self.floor[cell], fill=level_color(level / self.max_level))
        for nb in discovered:
            self.canvas.itemconfig(self.floor[nb], fill=FRONTIER)

        x, y = self.xy(cell)
        h = self.cs / 2
        self.canvas.delete("cursor")
        self.canvas.create_rectangle(x - h, y - h, x + h, y + h, outline=SHADOW, width=3, tags="cursor")
        self.raise_tokens()

        self.info["visited"].config(text=str(self.visited_count))
        self.info["queue"].config(text=str(queue_size))
        self.info["level"].config(text=str(level))

        if cell == self.goal:
            path = build_path(parent, self.goal)
            self.canvas.delete("cursor")
            self.draw_line(path, GOAL, "bfs_path")
            self.info["path"].config(text=str(len(path) - 1), fg=GOAL)
            self.say(f"BFS done: explored {self.visited_count} cells, shortest path = {len(path) - 1} steps.", GOAL)
            self.bfs_gen = None
            return True
        return False


if __name__ == "__main__":
    root = tk.Tk()
    MazeRunner(root)
    root.mainloop()
