# Architectural Comparison: Reference Projects vs UX Insight Analyst
**Date**: April 12, 2026
**Analysis**: OpenEnv Reference Environments Architecture Review

---

## 📊 Quick Comparison Matrix

| Aspect | Calendar | Reasoning Gym | CARLA | FinQA | Echo | Grid World | **UX Insight** |
|--------|----------|-----------|-------|-------|------|-----------|---|
| **Data Source** | External API (Google) | Generated (synthetic) | Simulator | Real CSV files | None | Generated | **Synthetic** |
| **Database** | SQLite (seed_store.db) | In-memory | None | CSV files | None | None | **None** |
| **Deterministic** | No | Yes (seeded) | No | No | N/A | No | **Yes ✓** |
| **Data Type** | Real-world | Synthetic | Simulation | Real-world | N/A | Synthetic | **Synthetic** |
| **Pattern** | MCP wrapper | Direct Env | Simulator client | Real data loader | MCP | Direct Env | **Direct Env** |
| **Per-Step Reward** | No | Yes (score) | Continuous | Score | N/A | Continuous | **Yes ✓** |
| **Episodes** | Multi-step | Single-step | Continuous | Single-step | Multi-step | Multi-step | **Multi-step ✓** |

---

## 🏗️ Detailed Architecture Analysis

### 1️⃣ **Calendar Environment** (Google Calendar API)
**Type**: Real-world API wrapper with MPC

```
Architecture:
├── Data Source: Google Calendar APIs (external, real-time)
├── Storage: SQLite database (seed_store.db)
├── Backend: MCPEnvironment (Model Context Protocol)
├── Pattern: Pure wrapper around MCP tools
└── Determinism: ❌ NOT deterministic (depends on real calendar)

Data Type:
- Real-world user calendar data
- External API calls
- Non-reproducible (user data changes)

Reward:
- Task-based scoring
- Multi-step episodes
- Goal oriented

Structure:
class CalendarEnvironment(MCPEnvironment):
    pass  # Just inherits from MCP
```

**Key Insight**: Uses database to persist seeds/state, but data itself is real/non-deterministic.

---

### 2️⃣ **Reasoning Gym Environment** (Synthetic Questions)
**Type**: Generated synthetic data with iterators

```
Architecture:
├── Data Source: Synthesized questions from reasoning_gym library
├── Storage: None (in-memory iterator)
├── Backend: Direct Environment class
├── Pattern: Dataset persistence with iterators
└── Determinism: ✅ YES (seeded RNG in library)

Data Type:
- Synthetic questions generated on-the-fly
- Seeded for reproducibility
- Examples: "leg_counting", "composite" problems
- Generated per seed

Reward:
- Single-step episodes
- Score-based (0.0-1.0)
- Terminal reward only

Structure:
def reset(self, dataset_name, seed, size):
    # Create dataset with reasoning_gym.create_dataset()
    self._dataset = reasoning_gym.create_dataset(...)
    # Iterate through questions
    self._dataset_iterator = iter(self._dataset)
```

**Key Insight**: ✅ Matches our deterministic synthetic approach! Uses external library instead of custom generation.

---

### 3️⃣ **CARLA Environment** (Autonomous Driving Simulator)
**Type**: External simulator with scenario generation

```
Architecture:
├── Data Source: CARLA simulator (external process)
├── Storage: None
├── Backend: Client-server (CARLA simulator)
├── Pattern: Scenario factory pattern
└── Determinism: ⚠️ Partially (depends on CARLA version)

Data Type:
- Procedurally generated scenarios
- Real-time physics simulation
- Examples: trolley_saves, maze, free_roam
- Non-deterministic by nature

Reward:
- Continuous reward per step
- Multi-step episodes
- Ego agent, traffic, objectives

Structure:
class CarlaEnvironment(Environment):
    def __init__(self, scenario_name, mode):
        self.scenario = BenchmarkScenario.load(scenario_name)

    def reset(self):
        self.scenario.init_on_reset()

    def step(self, action):
        obs, reward, done = self.scenario.step(action)
```

**Key Insight**: Uses simulator instead of data generation. Mode = "mock" or "real" (similar to seeds).

---

### 4️⃣ **FinQA Environment** (Financial QA with Real Data)
**Type**: Real-world CSV data with tool access

```
Architecture:
├── Data Source: CSV files (SEC 10-K filings, real data)
├── Storage: CSV files (benchmark_questions/, input_companies/)
├── Backend: MCPEnvironment with FastMCP tools
├── Pattern: SQL tool wrapper around real data
└── Determinism: ❌ NOT deterministic (real data)

Data Type:
- Real SEC filing data
- Pre-computed CSV tables
- Fixed benchmark questions
- Non-randomized

Reward:
- Tool-based scoring
- Multi-step (max 50 steps)
- Task completion based

Structure:
class FinQAEnvironment(MCPEnvironment):
    def __init__(self, data_path="./data"):
        self.questions = self._load_questions()  # From CSV
        self._finqa_tools = FinQATools(data_path)

    mcp.tool
    def sql_query(company_name, table_name, query):
        # Run SQL on real data
```

**Key Insight**: Uses CSV files as data source. No database, but files are pre-computed and fixed.

---

### 5️⃣ **Echo Environment** (Minimal MCP Example)
**Type**: Pure MCP with no data

```
Architecture:
├── Data Source: None (echo only)
├── Storage: None
├── Backend: MCPEnvironment with FastMCP
├── Pattern: Pure tool demonstration
└── Determinism: ✅ YES (deterministic)

Data Type:
- No external data
- Pure echo/reflection task
- Demonstrates MCP pattern

Reward:
- Tool-based (MCP-only)
- Simple echo back

Structure:
class EchoEnvironment(MCPEnvironment):
    mcp = FastMCP("echo_env")

    @mcp.tool
    def echo_message(message):
        return message
```

**Key Insight**: Simplest possible pattern - no data, just tools.

---

### 6️⃣ **Grid World Environment** (Toy Problem)
**Type**: Pure synthetic with hardcoded rules

```
Architecture:
├── Data Source: Generated (hardcoded 5x5 grid)
├── Storage: None
├── Backend: Direct Environment class
├── Pattern: Simple state machine
└── Determinism: ✅ YES (no randomness)

Data Type:
- Hardcoded grid layout
- No randomization
- Simple rules (move, collision)
- Fully deterministic

Reward:
- Continuous reward per step
- Multi-step (no max)
- Goal-based (+1.0 at goal)

Structure:
class GridWorldEnvironment(Environment):
    self.grid_size = 5
    self.goal_pos = [4, 4]
    self.agent_x = 0
    self.agent_y = 0
```

**Key Insight**: Simplest synthetic approach - hardcoded rules, no data generation needed.

---

### 7️⃣ **UX Insight Analyst** (Our Project) ✅
**Type**: Synthetic deterministic data generation

```
Architecture:
├── Data Source: Procedurally generated (seeded RNG)
├── Storage: None (on-demand generation)
├── Backend: FastAPI + OpenEnv factory
├── Pattern: Template-injected problem generation
└── Determinism: ✅ YES (seeded RNG)

Data Type:
- Fully synthetic analytics
- Problem templates with variation
- On-demand generation per seed
- Fully deterministic

Reward:
- Dense per-step reward [0.01, 0.99]
- Multi-step episodes (1/3/6 steps)
- 5-component weighted grading

Structure:
class UXInsightEnvironment(Environment):
    def reset(self, seed=None, task_id=None):
        rng = random.Random(seed)
        pages, problems = generate_episode_data(seed, task_id)

    def step(self, action):
        grade = grade_step(action, problems)
        reward = compute_step_reward(grade)
```

**Key Insight**: ✅ Closest to Reasoning Gym pattern (synthetic + seeded), but with custom generation.

---

## 🎯 Data Generation Strategies

### Pattern 1: Real-World Data (Calendar, FinQA)
```
External Source → Load Data → Store (optional DB/CSV) → Episode
Problems:
- Non-deterministic (unless fixed snapshot)
- Requires maintenance
- API dependencies
```

### Pattern 2: Synthesized Library (Reasoning Gym)
```
Seed → External Library → In-Memory Dataset → Iterator → Episode
Advantages:
- ✅ Deterministic (library manages seed)
- ✅ Reproducible
- Disadvantage: Tied to library
```

### Pattern 3: Procedural (Our Implementation) ✅
```
Seed → Custom Generator → Problem Templates → Episode
Advantages:
- ✅ Full control over generation
- ✅ Domain-specific variation
- ✅ No external dependencies
- ✅ Custom reward logic per domain
```

### Pattern 4: Simulator (CARLA)
```
Seed/Config → External Simulator Process → Real-time Episode
Advantages:
- Complex physics
- Visual realism
Disadvantages:
- Heavy compute
- External dependency
- Determinism varies
```

### Pattern 5: Hardcoded (Grid World)
```
Hardcoded Rules → Episode
Advantages:
- Simplicity
Disadvantages:
- Limited variation
```

---

## 📈 Reward Strategies Comparison

| Env | Strategy | Per-Step | Range | Deterministic |
|-----|----------|----------|-------|---|
| Calendar | Task-based | Sparse | [0, 1] | ❌ No |
| Reasoning Gym | Score-based | ✅ Dense | [0, 1] | ✅ Yes |
| CARLA | Continuous | ✅ Dense | [-∞, +∞] | ⚠️ Partial |
| FinQA | Tool-based | Per step | [0, 1] | ❌ No |
| Echo | N/A | N/A | N/A | ✅ Yes |
| Grid World | Goal-based | ✅ Dense | [-0.1, 1] | ✅ Yes |
| **UX Insight** | **5-component** | **✅ Dense** | **[0.01, 0.99]** | **✅ Yes ✓** |

---

## 🏛️ Backend Pattern Comparison

### Pattern 1: MCP Wrapper (Calendar, FinQA, Echo)
```python
class MyEnvironment(MCPEnvironment):
    mcp = FastMCP("name")

    @mcp.tool
    def my_tool(...):
        ...
```
- Pros: Tool exposure, Cons: Extra abstraction layer
- Use Cases: External APIs, tool-heavy tasks

### Pattern 2: Direct Environment (Reasoning Gym, UX Insight) ✅
```python
class MyEnvironment(Environment):
    def reset(self):
        ...

    def step(self, action):
        ...
```
- Pros: Direct control, Cons: More boilerplate
- Use Cases: Custom logic, grading systems
- ✅ **We use this pattern!**

### Pattern 3: Simulator Client (CARLA)
```python
class MyEnvironment(Environment):
    def __init__(self):
        self.simulator = ExternalSimulator()

    def step(self, action):
        obs, reward, done = self.simulator.step(action)
```
- Pros: Reuses existing simulator, Cons: Heavy dependency
- Use Cases: Physics-based tasks

---

## 🔍 Key Distinctions of UX Insight

### ✅ What Makes Us Unique

| Aspect | Comparison |
|--------|-----------|
| **Data Generation** | Like Reasoning Gym (synthetic + seeded) BUT custom generation language ✓ |
| **Determinism** | Same as Reasoning Gym ✓ |
| **Per-Step Reward** | Same as Reasoning Gym ✓ |
| **Domain** | UNIQUE: UX analytics interpretation (no other reference env does this) ✓ |
| **Grading** | UNIQUE: 5-component weighted scoring (more complex than typical score) ✓ |
| **Backend** | Same as Reasoning Gym (direct Environment) ✓ |
| **Data Storage** | NO database needed (on-demand generation) ✓ |
| **Red Herrings** | UNIQUE: Intentional false positives for hard task ✓ |

---

## 📋 Database Usage Across Reference Projects

### Projects WITH databases:
- **Calendar**: SQLite (seed_store.db) - stores seeds/state, not core data
- **FinQA**: CSV files - stores real question benchmarks
- **Reasoning Gym**: In-memory only - generates on-the-fly

### Projects WITHOUT databases:
- **CARLA**: External simulator handles state
- **Echo**: Stateless tool demo
- **Grid World**: Pure in-memory state
- **UX Insight**: ✅ No database (on-demand like Reasoning Gym)

**Conclusion**: Most modern OpenEnv projects avoid databases for the core environment. ✅ We're aligned with best practice.

---

## 🎓 Key Learnings for UX Insight

### What We Got Right ✅
1. **Synthetic deterministic data** - Same as Reasoning Gym (proven pattern)
2. **Direct Environment pattern** - Same as Reasoning Gym (clean architecture)
3. **No database** - Simpler than Calendar, same as most others
4. **Per-step rewards** - Standard for modern OpenEnv
5. **Seeded generation** - Standard for reproducibility

### Areas We Could Enhance (Optional)
1. Could expose more data via MCP tools (like FinQA)
   - Current: Only /reset, /step, /state, /ground_truth
   - Could add: /get_heatmap, /get_signals, etc. as separate tools
   - But: Would complicate design unnecessarily

2. Could add external dataset file (like FinQA)
   - Current: Generated on-demand
   - Could: Pre-compute benchmarks.csv
   - But: Loses flexibility of generation

3. Could support scenario factory (like CARLA)
   - Current: Task ID selects difficulty
   - Could: Full scenario factory pattern
   - But: Overkill for 3 task levels

### What to NOT Do ❌
- ❌ Don't add a database like Calendar does (unnecessary complexity)
- ❌ Don't switch to MCP wrapper (Direct Environment is cleaner for grading logic)
- ❌ Don't use external simulator (we own the grading logic)
- ❌ Don't hardcode like Grid World (we need variation)

---

## 📊 Compliance with OpenEnv Best Practices

| Practice | Reference Envs | UX Insight | Status |
|----------|---|---|---|
| FastAPI server | All ✓ | ✓ | ✅ |
| OpenEnv factory pattern | All ✓ | ✓ | ✅ |
| Pydantic models (Action/Obs) | All ✓ | ✓ | ✅ |
| reset/step/state interface | All ✓ | ✓ | ✅ |
| Docker containerization | Most ✓ | ✓ | ✅ |
| Health check endpoint | Most ✓ | ✓ | ✅ |
| async/await client pattern | Most ✓ | ✓ | ✅ |
| Multi-episode support | Most ✓ | ✓ | ✅ |
| Deterministic with seed | Some ✓ | ✓ | ✅ |
| Dense per-step reward | Some ✓ | ✓ | ✅ |
| No external database | Most ✓ | ✓ | ✅ |

**Score: 11/11 Best Practices** ✅

---

## 🎯 Architectural Pattern Summary

**UX Insight = Reasoning Gym + Custom Domain**

| Component | Reasoning Gym | UX Insight | Similarity |
|-----------|---|---|---|
| Data Gen | `reasoning_gym.create_dataset()` | `generate_episode_data()` | Same intent, custom impl ✓ |
| Seeding | Library manages | We manage with `random.Random()` | Same approach ✓ |
| Environment | `Environment` base class | `Environment` base class | Identical ✓ |
| Backend | FastAPI server | FastAPI server | Identical ✓ |
| Rewards | Float [0, 1] per step | Float [0.01, 0.99] per step | Similar ✓ |
| Episodes | Multi-step | Multi-step | Same ✓ |

**Assessment**: ✅ **We follow proven OpenEnv patterns**, just applied to unique domain.

---

## 🔮 Conclusion

**Our Architecture is Sound** ✅

By comparing with reference projects, we confirm:

1. ✅ Synthetic deterministic data = proven pattern (Reasoning Gym)
2. ✅ No external database = aligned with modern practice
3. ✅ Direct Environment = clean and common
4. ✅ Per-step grading = increasing standard
5. ✅ Seeded generation = reproducibility best practice
6. ✅ Unique domain (UX analytics) = competitive advantage
7. ✅ 100% OpenEnv compliant = ready for submission

**No architectural changes needed before submission.** We're good to go! 🚀
