# IPC & SYNCHRONIZATION ARCADE (PAC-MAN EDITION)
### Unified Operating Systems Simulation Suite
**Topic:** Interprocess Communication (IPC) and Process Synchronization  
**Technology:** Python 3 + Tkinter (Zero external pip dependencies)  
**Theme:** 1980s Classic Pac-Man Arcade Aesthetic  

---

## 🎮 Quick Start

You can run the simulation in either of two ways:

### Option A: Double-Click the Launcher (Recommended)
Simply double-click `run.bat` in File Explorer, or in PowerShell run:
```powershell
.\run.bat
```

### Option B: Run via Python Directly
```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" ipc_simulator.py
```
*(or `python ipc_simulator.py` if Python is added to your PATH)*

Run the automated test suite:

```powershell
python -m unittest test_ipc_simulator.py -v
```

---

## 🕹️ Project Features

### Module 1: IPC & Synchronization (Core Assigned Module)
- **Message Passing & Mailbox Models:** Supports both Mailbox (Indirect) and Direct addressing modes with structured packet headers (`msg_id`, `sender`, `receiver`, `payload`, `size`, `timestamp`).
- **Send & Receive Operations:** Manual send/receive with quick arcade presets (`Power Pellet`, `Cherry`, `Strawberry`, `Speed Boost`, `Radar Scan`, `Secret Key`).
- **Bounded Buffer & Ring Queue:** Circular array with visual slot indices (`0` to `N-1`), occupied state indicators, and `IN`/`OUT` pointer markers.
- **Backpressure & Starvation Demonstrations:** 
  - Buffer full triggers Producer `BLOCKED` state on `wait(empty)`.
  - Buffer empty triggers Consumer `BLOCKED` state on `wait(full)`.
- **Dijkstra's Three Semaphores:** Real-time visual meters for `mutex` (Binary), `empty` (Counting), and `full` (Counting) semaphores, maintaining the conservation law:
  $$\text{empty\_sem} + \text{full\_sem} = \text{Capacity}$$
- **Live Pseudocode Tracer:** Line-by-line real-time visual code highlighter showing the exact semaphore synchronization sequence during execution.
- **Packet Inspector:** Click on any slot to inspect the underlying OS message packet envelope.
- **Automated Rate Generators:** Independent interval sliders for Auto-Producer and Auto-Consumer to simulate asynchronous rate mismatches.
- **Challenge Missions:** 4 gamified laboratory missions testing basic dispatch, overflow backpressure, starvation relief, and rate balancing.
- **Arcade Quiz Battle:** 5-question interactive multiple choice OS quiz with feedback and animated Pac-Man progress tracker.
- **Concept Guide:** Complete textbook-grade reference manual on IPC and process synchronization.
- **8-Bit Retro Sound Engine:** Non-blocking arcade sound effects using standard Windows audio with mute/unmute toggle.

### Modules 2 to 6: Integrated Companion Simulations
- **Module 2: CPU Scheduling Arcade:** Interactive Gantt chart for FCFS, Shortest Job First (SJF), and Round Robin (RR) with Pac-Man CPU eater.
- **Module 3: Memory Management Arcade:** Physical frame matrix (4×4 grid) simulating contiguous allocation, paging, and out-of-memory errors.
- **Module 4: Deadlock & Philosophers Arcade:** 4 Ghosts competing for 4 power chopsticks, demonstrating Coffman's 4 conditions, circular wait, and deadlock prevention.
- **Module 5: File Systems Arcade:** Circular 12-sector disk map simulating Inode index blocks, file creation, and sector allocation.
- **Module 6: Process Management Arcade:** 5-state process lifecycle state machine (`NEW` $\rightarrow$ `READY` $\rightarrow$ `RUNNING` $\rightarrow$ `WAITING` $\rightarrow$ `TERMINATED`) with live Process Control Block (PCB) inspector.

---

## 📂 Deliverables & File Manifest

| File | Purpose |
| :--- | :--- |
| `ipc_simulator.py` | Complete, functional, self-contained Python source code for the unified simulation suite. |
| `test_ipc_simulator.py` | Automated test suite (10 unit & integration tests, 100% pass rate). |
| `TECHNICAL_DOCUMENTATION.md` | Formal explanation of system architecture, Dijkstra's algorithm, mathematical invariants, and data structures. |
| `USER_GUIDE.md` | Step-by-step user manual with screen walkthroughs and keyboard shortcuts. |
| `TESTING_RESULTS.md` | Formal testing report with requirement compliance matrix and edge-case validation. |
| `DEMONSTRATION_GUIDE.md` | Live presentation roadmap (5-minute and 10-minute scripts) and Q&A defense cheat sheet. |
| `README.md` | Repository overview and quick start instructions. |
