from abc import ABC, abstractmethod


class BaseEnricher(ABC):

    @abstractmethod
    def enrich(
        self,
        file_path,
        source_code,
        graph_data
    ):
        pass