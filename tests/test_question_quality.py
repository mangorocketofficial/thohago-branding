from __future__ import annotations

import unittest

from thohago.web.services.question_quality import question_looks_invalid


class QuestionQualityTests(unittest.TestCase):
    def test_customer_inner_state_question_is_invalid(self) -> None:
        self.assertTrue(question_looks_invalid("고객은 어떤 기분이셨나요?"))

    def test_service_recipient_question_without_owner_anchor_is_invalid(self) -> None:
        self.assertTrue(question_looks_invalid("장비에 의해 머리가 마사지되는 순간, 어떤 느낌이셨나요?"))

    def test_owner_observation_question_is_valid(self) -> None:
        self.assertFalse(question_looks_invalid("그 장면에서 사장님이 보신 고객 반응이나 표정 중 가장 기억에 남는 순간이 있었나요?"))

    def test_owner_perspective_question_is_valid(self) -> None:
        self.assertFalse(question_looks_invalid("이 경험이 사장님께는 어떤 의미로 기억되시나요?"))


if __name__ == "__main__":
    unittest.main()
