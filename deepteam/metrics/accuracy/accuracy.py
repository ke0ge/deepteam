from typing import Optional, Tuple, Union

from deepteam.test_case import RTTestCase
from deepeval.utils import get_or_create_event_loop
from deepeval.metrics.utils import (
    construct_verbose_logs,
    trimAndLoadJson,
    initialize_model,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.metrics.indicator import metric_progress_indicator

from deepteam.metrics import BaseRedTeamingMetric
from deepteam.metrics.harm.schema import ReasonScore # Can reuse the same schema
from deepteam.metrics.accuracy.template import AccuracyTemplate
from deepteam.utils import format_turns


class AccuracyMetric(BaseRedTeamingMetric):
    def __init__(
        self,
        context: str, # The critical context to check against, e.g., "Scientific medical knowledge"
        model: Optional[Union[str, DeepEvalBaseLLM]] = None,
        async_mode: bool = True,
        verbose_mode: bool = False,
    ):
        self.context = context
        self.model, self.using_native_model = initialize_model(model)
        self.evaluation_model = self.model.get_model_name()
        self.async_mode = async_mode
        self.verbose_mode = verbose_mode

    def measure(self, test_case: RTTestCase) -> float:
        self.evaluation_cost = 0 if self.using_native_model else None
        with metric_progress_indicator(self, _show_indicator=False):
            if self.async_mode:
                loop = get_or_create_event_loop()
                return loop.run_until_complete(
                    self.a_measure(test_case, _show_indicator=False)
                )
            else:
                score, reason = self.evaluate(test_case)
                self.reason = reason
                self.score = score
                self.success = self.score == 1
                self.verbose_logs = construct_verbose_logs(
                    self,
                    steps=[f"Score: {self.score}\nReason: {self.reason}"],
                )
                return self.score

    async def a_measure(
        self,
        test_case: RTTestCase,
        _show_indicator: bool = False,
    ) -> float:
        self.evaluation_cost = 0 if self.using_native_model else None
        with metric_progress_indicator(
            self,
            async_mode=True,
            _show_indicator=_show_indicator,
        ):
            score, reason = await self._a_evaluate(test_case)
            self.reason = reason
            self.score = score
            self.success = self.score == 1
            self.verbose_logs = construct_verbose_logs(
                self,
                steps=[f"Score: {self.score}\nReason: {self.reason}"],
            )
            return self.score

    async def _a_evaluate(self, test_case: RTTestCase) -> Tuple[Union[int, float], str]:
        actual_output = format_turns(test_case.turns) if test_case.turns else test_case.actual_output
        prompt = AccuracyTemplate.generate_evaluation_results(
            input=test_case.input,
            actual_output=actual_output,
            context=self.context,
        )
        if self.using_native_model:
            res, cost = await self.model.a_generate(prompt=prompt, schema=ReasonScore)
            self.evaluation_cost += cost
            return res.score, res.reason
        else:
            try:
                res: ReasonScore = await self.model.a_generate(prompt=prompt, schema=ReasonScore)
                return res.score, res.reason
            except TypeError:
                res = await self.model.a_generate(prompt)
                data = trimAndLoadJson(res, self)
                return data["score"], data["reason"]

    def evaluate(self, test_case: RTTestCase) -> Tuple[Union[int, float], str]:
        actual_output = format_turns(test_case.turns) if test_case.turns else test_case.actual_output
        prompt = AccuracyTemplate.generate_evaluation_results(
            input=test_case.input,
            actual_output=actual_output,
            context=self.context,
        )
        if self.using_native_model:
            res, cost = self.model.generate(prompt=prompt, schema=ReasonScore)
            self.evaluation_cost += cost
            return res.score, res.reason
        else:
            try:
                res: ReasonScore = self.model.generate(prompt=prompt, schema=ReasonScore)
                return res.score, res.reason
            except TypeError:
                res = self.model.generate(prompt)
                data = trimAndLoadJson(res, self)
                return data["score"], data["reason"]

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            self.success = self.score == 1
        return self.success

    @property
    def __name__(self):
        return f"Accuracy (Red Teaming)"
