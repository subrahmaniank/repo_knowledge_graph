from enrichers.angular.enricher import AngularEnricher

from enrichers.react.enricher import ReactEnricher
from enrichers.react_router.enricher import ReactRouterEnricher

from enrichers.spring.enricher import SpringBootEnricher

from enrichers.flask.enricher import FlaskEnricher


class EnricherFactory:
    @staticmethod
    def get_enrichers(file_path, source_code):

        enrichers = []

        path = str(file_path).lower()

        #
        # ANGULAR
        #
        if path.endswith(".ts"):
            if (
                "@Component" in source_code
                or "@Injectable" in source_code
                or "@NgModule" in source_code
            ):
                enrichers.append(AngularEnricher())

        #
        # REACT
        #
        if path.endswith(".jsx") or path.endswith(".tsx"):
            enrichers.append(ReactEnricher())

        #
        # REACT ROUTER
        #
        if (
            "react-router" in source_code
            or "<Route" in source_code
            or "BrowserRouter" in source_code
        ):
            enrichers.append(ReactRouterEnricher())
        #
        # SPRING BOOT
        #
        if path.endswith(".java"):
            if (
                "@SpringBootApplication" in source_code
                or "@RestController" in source_code
                or "@Service" in source_code
                or "@Repository" in source_code
            ):
                enrichers.append(SpringBootEnricher())

        #
        # FLASK
        #
        if path.endswith(".py"):
            if (
                "Flask(" in source_code
                or "@app.route" in source_code
                or "Blueprint(" in source_code
            ):
                enrichers.append(FlaskEnricher())

        return enrichers
