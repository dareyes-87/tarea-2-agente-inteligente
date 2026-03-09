import tkinter as tk
import random
import heapq

CELL = 28
GRID = 20

BG       = "#0a0e1a"
BG_CELL  = "#111827"
BG_PANEL = "#0f1628"
OBSTACLE = "#2d3a52"
HUNTER_C = "#ef4444"
PREY_C   = "#06b6d4"
ACCENT   = "#f59e0b"
TEXT_C   = "#e2e8f0"
DIM_C    = "#64748b"
GRID_L   = "#1e293b"


class AgentWorld:
    def __init__(self, root):
        self.root = root
        self.root.title("Agente Inteligente — Cazador vs Presa")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.step    = 0
        self.catches = 0
        self.running = False
        self.speed   = 400   # ms entre pasos

        self._init_world()
        self._build_ui()
        self._draw()

    # ── Inicializar posiciones y obstáculos ──────────────────────────────────
    def _init_world(self):
        self.hunter = (random.randint(0, GRID-1), random.randint(0, GRID-1))
        self.prey   = (random.randint(0, GRID-1), random.randint(0, GRID-1))
        while self.prey == self.hunter:
            self.prey = (random.randint(0, GRID-1), random.randint(0, GRID-1))

        self.obstacles = set()
        while len(self.obstacles) < 45:
            c = (random.randint(0, GRID-1), random.randint(0, GRID-1))
            if c != self.hunter and c != self.prey:
                self.obstacles.add(c)

        self.path      = []   # camino actual del cazador (A*)
        self.flee_path = []   # siguiente celda de huida de la presa
        self.step      = 0

    # ── Construcción de la interfaz ──────────────────────────────────────────
    def _build_ui(self):
        tk.Label(self.root, text="🧠 Agente Inteligente — Cazador vs Presa",
                 font=("Courier New", 13, "bold"), fg=ACCENT, bg=BG)\
            .pack(pady=(10, 2))

        frame = tk.Frame(self.root, bg=BG)
        frame.pack(padx=10, pady=6)

        self.canvas = tk.Canvas(frame, width=CELL*GRID, height=CELL*GRID,
                                bg=BG_CELL, highlightthickness=1,
                                highlightbackground=GRID_L)
        self.canvas.grid(row=0, column=0, padx=(0, 12))

        panel = tk.Frame(frame, bg=BG_PANEL, width=230)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_propagate(False)
        self._build_panel(panel)

    def _build_panel(self, p):
        def sep():
            tk.Frame(p, bg=ACCENT, height=1).pack(fill="x", padx=12, pady=4)

        def section(title):
            tk.Label(p, text=title, font=("Courier New", 8, "bold"),
                     fg=ACCENT, bg=BG_PANEL).pack(anchor="w", padx=12, pady=(6,0))
            sep()

        def stat_row(label):
            f = tk.Frame(p, bg=BG_PANEL)
            f.pack(fill="x", padx=12, pady=1)
            tk.Label(f, text=label+":", font=("Courier New", 8),
                     fg=DIM_C, bg=BG_PANEL, width=14, anchor="w").pack(side="left")
            v = tk.Label(f, text="—", font=("Courier New", 8, "bold"),
                         fg=TEXT_C, bg=BG_PANEL)
            v.pack(side="left")
            return v

        # ── Leyenda ──────────────────────────────────────────────────────────
        section("▸ LEYENDA")
        for color, desc in [(HUNTER_C, "🔴 Cazador  — usa A*"),
                            (PREY_C,   "🔵 Presa    — huye greedy"),
                            ("#1d3a6e","▪  Camino del cazador"),
                            ("#2d1f4e","▪  Siguiente paso presa")]:
            tk.Label(p, text=desc, font=("Courier New", 8),
                     fg=color, bg=BG_PANEL).pack(anchor="w", padx=16, pady=1)

        # ── Estadísticas ─────────────────────────────────────────────────────
        section("▸ ESTADÍSTICAS")
        self.lbl_step    = stat_row("Pasos")
        self.lbl_dist    = stat_row("Distancia")
        self.lbl_plen    = stat_row("Nodos en path")
        self.lbl_catches = stat_row("Capturas")

        # ── Posiciones ───────────────────────────────────────────────────────
        section("▸ POSICIONES")
        self.lbl_hpos   = stat_row("Cazador (x,y)")
        self.lbl_ppos   = stat_row("Presa   (x,y)")
        self.lbl_action = stat_row("Estado")

        # ── Velocidad ────────────────────────────────────────────────────────
        section("▸ VELOCIDAD")
        self.speed_var = tk.IntVar(value=self.speed)
        tk.Scale(p, from_=100, to=900, orient="horizontal",
                 variable=self.speed_var, bg=BG_PANEL, fg=TEXT_C,
                 troughcolor="#1e293b", highlightthickness=0,
                 font=("Courier New", 7), label="ms / paso",
                 command=lambda v: setattr(self, "speed", int(v)))\
            .pack(fill="x", padx=12, pady=(0, 4))

        # ── Controles ────────────────────────────────────────────────────────
        section("▸ CONTROLES")
        for txt, color, cmd in [("▶  Iniciar",   "#10b981", self._start),
                                 ("⏸  Pausar",    ACCENT,    self._pause),
                                 ("↺  Reiniciar", DIM_C,     self._reset)]:
            tk.Button(p, text=txt, command=cmd, bg=BG_CELL, fg=color,
                      font=("Courier New", 8, "bold"), relief="flat",
                      activebackground="#1e293b", activeforeground=color,
                      cursor="hand2", pady=5)\
                .pack(fill="x", padx=12, pady=2)

    # ── Heurística Manhattan ─────────────────────────────────────────────────
    def _h(self, a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    # ── Vecinos válidos (sin obstáculos, dentro del grid) ────────────────────
    def _neighbors(self, node):
        x, y = node
        return [(x+dx, y+dy)
                for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]
                if 0 <= x+dx < GRID and 0 <= y+dy < GRID
                and (x+dx, y+dy) not in self.obstacles]

    # ── A* : encuentra el camino más corto de start a goal ──────────────────
    def _astar(self, start, goal):
        pq = [(0, start)]
        came, cost = {}, {start: 0}
        while pq:
            _, cur = heapq.heappop(pq)
            if cur == goal:
                break
            for n in self._neighbors(cur):
                nc = cost[cur] + 1
                if n not in cost or nc < cost[n]:
                    cost[n] = nc
                    heapq.heappush(pq, (nc + self._h(goal, n), n))
                    came[n] = cur
        path, node = [], goal
        while node != start and node in came:
            path.append(node); node = came[node]
        path.reverse()
        return path

    # ── Cazador: avanza un paso por el camino A* ────────────────────────────
    def _move_hunter(self):
        self.path = self._astar(self.hunter, self.prey)
        if self.path:
            self.hunter = self.path.pop(0)

    # ── Presa: huye al vecino más lejano del cazador (greedy) ────────────────
    def _move_prey(self):
        nbrs = self._neighbors(self.prey)
        if not nbrs:
            return
        # Excluye la posición actual del cazador para evitar bucles de oscilación
        safe = [n for n in nbrs if n != self.hunter]
        candidates = safe if safe else nbrs   # si no hay escapatoria, usa todos
        best = max(candidates, key=lambda n: self._h(n, self.hunter))
        self.flee_path = [best]
        self.prey = best

    # ── Un paso de simulación ─────────────────────────────────────────────────
    def _update(self):
        if not self.running:
            return

        self.step += 1
        self._move_hunter()

        if self.hunter == self.prey:
            self.catches += 1
            self._refresh_stats("¡Captura!")
            self._draw()
            self._reset_positions()
            self.root.after(700, self._tick)
            return

        self._move_prey()
        self._refresh_stats("Persiguiendo")
        self._draw()
        self._tick()

    def _tick(self):
        if self.running:
            self.root.after(self.speed, self._update)

    # ── Actualizar etiquetas del panel ────────────────────────────────────────
    def _refresh_stats(self, action):
        d = self._h(self.hunter, self.prey)
        self.lbl_step   .config(text=str(self.step))
        self.lbl_dist   .config(text=str(d))
        self.lbl_plen   .config(text=str(len(self.path)))
        self.lbl_catches.config(text=str(self.catches))
        self.lbl_hpos   .config(text=str(self.hunter))
        self.lbl_ppos   .config(text=str(self.prey))
        self.lbl_action .config(text=action,
                                 fg=HUNTER_C if action=="¡Captura!" else TEXT_C)

    # ── Controles ────────────────────────────────────────────────────────────
    def _start(self):
        if not self.running:
            self.running = True
            self._tick()

    def _pause(self):
        self.running = False

    def _reset(self):
        self.running = False
        self.catches = 0
        self._init_world()
        self._refresh_stats("—")
        self._draw()

    def _reset_positions(self):
        self.hunter = (random.randint(0, GRID-1), random.randint(0, GRID-1))
        self.prey   = (random.randint(0, GRID-1), random.randint(0, GRID-1))
        while self.prey == self.hunter:
            self.prey = (random.randint(0, GRID-1), random.randint(0, GRID-1))
        self.path = []; self.flee_path = []

    # ── Dibujar el grid ───────────────────────────────────────────────────────
    def _draw(self):
        self.canvas.delete("all")
        path_set = set(self.path)
        flee_set = set(self.flee_path)

        for x in range(GRID):
            for y in range(GRID):
                x1, y1 = x*CELL, y*CELL
                x2, y2 = x1+CELL, y1+CELL
                cell = (x, y)

                if   cell == self.hunter:    color = HUNTER_C
                elif cell == self.prey:      color = PREY_C
                elif cell in self.obstacles: color = OBSTACLE
                elif cell in path_set:       color = "#1d3a6e"
                elif cell in flee_set:       color = "#2d1f4e"
                else:                        color = BG_CELL

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline=GRID_L, width=1)

        # Íconos sobre las celdas de los agentes
        hx, hy = self.hunter
        self.canvas.create_text(hx*CELL+CELL//2, hy*CELL+CELL//2,
                                text="🔴", font=("", 12))
        px, py = self.prey
        self.canvas.create_text(px*CELL+CELL//2, py*CELL+CELL//2,
                                text="🔵", font=("", 12))

        # Línea punteada que une a los dos agentes
        self.canvas.create_line(hx*CELL+CELL//2, hy*CELL+CELL//2,
                                px*CELL+CELL//2, py*CELL+CELL//2,
                                fill=ACCENT, dash=(4, 4), width=1)


# ── Punto de entrada ──────────────────────────────────────────────────────────
root = tk.Tk()
app  = AgentWorld(root)
root.mainloop()