from __future__ import annotations

from typing import Optional

from schift._http import HttpClient


class WorkflowsModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def create(self, name: str, description: Optional[str] = None, template: Optional[str] = None, graph: Optional[dict] = None):
        payload = {"name": name}
        if description is not None:
            payload["description"] = description
        if template is not None:
            payload["template"] = template
        if graph is not None:
            payload["graph"] = graph
        return self._http.post("/workflows", data=payload)

    def list(self):
        return self._http.get("/workflows")

    def get(self, workflow_id: str):
        return self._http.get(f"/workflows/{workflow_id}")

    def update(self, workflow_id: str, name: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None, graph: Optional[dict] = None):
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        if graph is not None:
            payload["graph"] = graph
        return self._http.patch(f"/workflows/{workflow_id}", data=payload)

    def delete(self, workflow_id: str):
        return self._http.delete(f"/workflows/{workflow_id}")

    def add_block(self, workflow_id: str, block_id: str, type: str, config: Optional[dict] = None, position: Optional[dict] = None):
        payload = {"block_id": block_id, "type": type}
        if config is not None:
            payload["config"] = config
        if position is not None:
            payload["position"] = position
        return self._http.post(f"/workflows/{workflow_id}/blocks", data=payload)

    def remove_block(self, workflow_id: str, block_id: str):
        return self._http.delete(f"/workflows/{workflow_id}/blocks/{block_id}")

    def add_edge(self, workflow_id: str, source: str, target: str, source_port: Optional[str] = None, target_port: Optional[str] = None):
        payload = {"source": source, "target": target}
        if source_port is not None:
            payload["source_port"] = source_port
        if target_port is not None:
            payload["target_port"] = target_port
        return self._http.post(f"/workflows/{workflow_id}/edges", data=payload)

    def remove_edge(self, workflow_id: str, edge_id: str):
        return self._http.delete(f"/workflows/{workflow_id}/edges/{edge_id}")

    def run(self, workflow_id: str, inputs: Optional[dict] = None, mode: str = "sync"):
        """Execute a workflow.

        Args:
            workflow_id: Workflow ID.
            inputs: Execution inputs.
            mode: ``"sync"`` (default) blocks until complete;
                  ``"async"`` returns ``{"id": ..., "workflow_id": ..., "status": "pending"}``
                  immediately — poll with :meth:`get_run` / :meth:`get_run_logs`.
        """
        qs = f"?mode={mode}" if mode != "sync" else ""
        return self._http.post(f"/workflows/{workflow_id}/run{qs}", data={"inputs": inputs or {}})

    def run_async(self, workflow_id: str, inputs: Optional[dict] = None):
        """Shorthand for ``run(workflow_id, inputs, mode="async")``."""
        return self.run(workflow_id, inputs, mode="async")

    def list_runs(self, workflow_id: str):
        return self._http.get(f"/workflows/{workflow_id}/runs")

    def get_run(self, workflow_id: str, run_id: str):
        return self._http.get(f"/workflows/{workflow_id}/runs/{run_id}")

    def get_run_logs(self, workflow_id: str, run_id: str, after_seq: int = 0):
        """Get per-block execution logs for a run.

        Args:
            after_seq: Only return logs with ``seq > after_seq`` (for polling).
        """
        qs = f"?after_seq={after_seq}" if after_seq > 0 else ""
        return self._http.get(f"/workflows/{workflow_id}/runs/{run_id}/logs{qs}")

    def validate(self, workflow_id: str):
        return self._http.post(f"/workflows/{workflow_id}/validate")

    def import_yaml(self, yaml_str: str):
        return self._http.post("/workflows/import", data={"yaml": yaml_str})

    def export_yaml(self, workflow_id: str):
        return self._http.get(f"/workflows/{workflow_id}/export")

    def generate(self, prompt: str, model: Optional[str] = None):
        payload = {"prompt": prompt}
        if model is not None:
            payload["model"] = model
        return self._http.post("/workflows/generate", data=payload)

    def block_types(self):
        return self._http.get("/workflows/meta/block-types")

    def templates(self):
        return self._http.get("/workflows/meta/templates")
