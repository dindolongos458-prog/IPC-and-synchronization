"""
Comprehensive Automated Unit & Integration Test Suite
for IPC & Synchronization Simulator (Pac-Man Arcade Edition)
============================================================
Tests core data structures, semaphore invariants, bounded buffer edge cases,
process state transitions, and GUI integration.
"""

import unittest
import tkinter as tk
from ipc_simulator import (
    MessagePacket,
    BoundedBufferQueue,
    ProcessState,
    IPCSyncApp,
    IPCSyncModule,
)


class TestMessagePacket(unittest.TestCase):
    """Test IPC Message Packet encapsulation and metadata."""

    def test_packet_creation(self):
        pkt = MessagePacket(
            msg_id=1,
            sender="Pac-Man [PID: 101]",
            receiver="Blinky [PID: 202]",
            msg_type="Power Pellet",
            payload="Test Message",
            icon="🟡",
            priority=1
        )
        self.assertEqual(pkt.msg_id, 1)
        self.assertEqual(pkt.sender, "Pac-Man [PID: 101]")
        self.assertEqual(pkt.receiver, "Blinky [PID: 202]")
        self.assertEqual(pkt.payload, "Test Message")
        self.assertGreater(pkt.size_bytes, 16)
        self.assertIn("🟡", pkt.short_display())


class TestBoundedBufferQueue(unittest.TestCase):
    """Test Dijkstra's Three-Semaphore Bounded Buffer implementation."""

    def setUp(self):
        self.capacity = 5
        self.queue = BoundedBufferQueue(capacity=self.capacity)

    def test_initial_semaphore_invariants(self):
        """Invariant: empty_sem == capacity, full_sem == 0, mutex == 1."""
        self.assertEqual(self.queue.capacity, self.capacity)
        self.assertEqual(self.queue.count, 0)
        self.assertEqual(self.queue.empty_sem, self.capacity)
        self.assertEqual(self.queue.full_sem, 0)
        self.assertEqual(self.queue.mutex, 1)
        self.assertTrue(self.queue.is_empty)
        self.assertFalse(self.queue.is_full)

    def test_enqueue_and_fifo_order(self):
        """Enqueue multiple packets and verify First-In-First-Out ordering."""
        p1 = MessagePacket(1, "A", "B", "Type", "First")
        p2 = MessagePacket(2, "A", "B", "Type", "Second")
        p3 = MessagePacket(3, "A", "B", "Type", "Third")

        ok1, _ = self.queue.enqueue(p1)
        ok2, _ = self.queue.enqueue(p2)
        ok3, _ = self.queue.enqueue(p3)

        self.assertTrue(ok1 and ok2 and ok3)
        self.assertEqual(self.queue.count, 3)
        self.assertEqual(self.queue.empty_sem, 2)
        self.assertEqual(self.queue.full_sem, 3)

        # Dequeue must return p1, then p2, then p3
        out1, _ = self.queue.dequeue()
        out2, _ = self.queue.dequeue()
        out3, _ = self.queue.dequeue()

        self.assertEqual(out1.payload, "First")
        self.assertEqual(out2.payload, "Second")
        self.assertEqual(out3.payload, "Third")
        self.assertTrue(self.queue.is_empty)

    def test_buffer_full_condition(self):
        """Test bounded buffer backpressure when full (empty_sem == 0)."""
        for i in range(self.capacity):
            ok, _ = self.queue.enqueue(MessagePacket(i, "A", "B", "Type", f"Msg {i}"))
            self.assertTrue(ok)

        self.assertTrue(self.queue.is_full)
        self.assertEqual(self.queue.empty_sem, 0)
        self.assertEqual(self.queue.full_sem, self.capacity)

        # Overflow attempt must fail
        overflow_ok, reason = self.queue.enqueue(MessagePacket(99, "A", "B", "Type", "Overflow"))
        self.assertFalse(overflow_ok)
        self.assertIn("FULL", reason)

    def test_buffer_empty_condition(self):
        """Test consumer starvation when empty (full_sem == 0)."""
        self.assertTrue(self.queue.is_empty)
        out, reason = self.queue.dequeue()
        self.assertIsNone(out)
        self.assertIn("EMPTY", reason)

    def test_semaphore_sum_invariant(self):
        """At all times, empty_sem + full_sem must equal buffer capacity."""
        for i in range(self.capacity):
            self.queue.enqueue(MessagePacket(i, "A", "B", "Type", f"Msg {i}"))
            self.assertEqual(self.queue.empty_sem + self.queue.full_sem, self.capacity)

        for _ in range(self.capacity):
            self.queue.dequeue()
            self.assertEqual(self.queue.empty_sem + self.queue.full_sem, self.capacity)

    def test_dynamic_buffer_resize(self):
        """Resizing buffer must rebalance empty_sem and full_sem properly."""
        self.queue.enqueue(MessagePacket(1, "A", "B", "Type", "Msg 1"))
        self.queue.enqueue(MessagePacket(2, "A", "B", "Type", "Msg 2"))
        self.assertEqual(self.queue.count, 2)

        # Expand to 8 slots
        self.queue.resize(8)
        self.assertEqual(self.queue.capacity, 8)
        self.assertEqual(self.queue.count, 2)
        self.assertEqual(self.queue.empty_sem, 6)
        self.assertEqual(self.queue.full_sem, 2)
        self.assertEqual(self.queue.empty_sem + self.queue.full_sem, 8)


class TestIPCGUIIntegration(unittest.TestCase):
    """Integration test suite for the unified GUI and process simulator."""

    def setUp(self):
        self.root = tk.Tk()
        self.app = IPCSyncApp(self.root)
        self.root.update()

    def tearDown(self):
        if hasattr(self.app, "frames"):
            for f in self.app.frames.values():
                if hasattr(f, "on_hide"):
                    f.on_hide()
        self.root.update()
        self.root.destroy()

    def test_navigation_to_all_six_modules(self):
        """Verify seamless navigation to all 6 modules and home dashboard."""
        module_keys = ["home", "ipc_sync", "cpu_sched", "mem_mgmt", "deadlock", "file_sys", "proc_mgmt"]
        for key in module_keys:
            self.app._navigate(key)
            self.root.update()
            self.assertEqual(self.app.current_key, key)

    def test_producer_consumer_lifecycle_in_gui(self):
        """Verify send, receive, blocked full, and blocked empty states."""
        ipc_mod: IPCSyncModule = self.app.frames["ipc_sync"]
        self.app._navigate("ipc_sync")
        self.root.update()

        # Initial clean state
        self.assertEqual(ipc_mod.buffer.count, 0)
        self.assertEqual(ipc_mod.proc_a_state, ProcessState.RUNNING)
        self.assertEqual(ipc_mod.proc_b_state, ProcessState.RUNNING)

        # Send one item
        ipc_mod.entry_msg.delete(0, "end")
        ipc_mod.entry_msg.insert(0, "Speed Boost")
        ipc_mod.do_send()
        self.root.update()
        self.assertEqual(ipc_mod.buffer.count, 1)

        # Receive item
        ipc_mod.do_receive()
        self.root.update()
        self.assertEqual(ipc_mod.buffer.count, 0)

        # Trigger buffer empty block
        ipc_mod.do_receive()
        self.root.update()
        self.assertEqual(ipc_mod.proc_b_state, ProcessState.BLOCKED)

        # Send items until buffer is full
        cap = ipc_mod.buffer.capacity
        for _ in range(cap):
            ipc_mod.do_send()
            self.root.update()
        self.assertEqual(ipc_mod.buffer.count, cap)

        # Trigger buffer full block
        ipc_mod.do_send()
        self.root.update()
        self.assertEqual(ipc_mod.proc_a_state, ProcessState.BLOCKED)

        # Reset
        ipc_mod.do_reset()
        self.root.update()
        self.assertEqual(ipc_mod.buffer.count, 0)
        self.assertEqual(ipc_mod.proc_a_state, ProcessState.RUNNING)
        self.assertEqual(ipc_mod.proc_b_state, ProcessState.RUNNING)

    def test_quiz_and_missions_subtabs(self):
        """Verify game learning sub-tabs (Missions, Quiz, Guide, Arena)."""
        ipc_mod: IPCSyncModule = self.app.frames["ipc_sync"]
        self.app._navigate("ipc_sync")

        # Sub-tab switching
        for sub in ["missions", "quiz", "guide", "arena"]:
            ipc_mod._switch_sub_tab(sub)
            self.root.update()
            self.assertEqual(ipc_mod.sub_mode_var.get(), sub)

        # Test answering quiz question
        ipc_mod._switch_sub_tab("quiz")
        self.root.update()
        initial_score = ipc_mod.quiz_score
        ipc_mod._on_quiz_answer(1)  # Answer option 1
        self.root.update()
        self.assertGreaterEqual(ipc_mod.quiz_score, initial_score)


if __name__ == "__main__":
    unittest.main()
