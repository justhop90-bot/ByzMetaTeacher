from __future__ import annotations

import unittest

from LearnerAI.Compiler.primitives import default_de_registry


class NativeChatContractTests(unittest.TestCase):
    def test_chat_actions_are_executable_native_primitives(self) -> None:
        registry = default_de_registry()

        player = registry.get("chat-to-player")
        allies = registry.get("chat-to-allies")

        self.assertIsNotNone(player)
        self.assertIsNotNone(allies)
        assert player is not None
        assert allies is not None

        self.assertEqual(player.kind, "ACTION")
        self.assertEqual((player.min_args, player.max_args), (2, 2))
        self.assertEqual(allies.kind, "ACTION")
        self.assertEqual((allies.min_args, allies.max_args), (1, 1))

    def test_chat_actions_are_executable_safe_presentation_actions(self) -> None:
        registry = default_de_registry()
        self.assertEqual(
            registry.assess_support("chat-to-player").state.value,
            "executable-safe",
        )
        self.assertEqual(
            registry.assess_support("chat-to-allies").state.value,
            "executable-safe",
        )

    def test_debug_self_chat_is_not_promoted(self) -> None:
        registry = default_de_registry()
        self.assertIsNone(registry.get("chat-local-to-self"))


if __name__ == "__main__":
    unittest.main()
