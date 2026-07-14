"""Prompt template loader with variable interpolation.

Loads ``.txt`` prompt templates from the ``prompts/`` directory and supports
``{variable}``-style placeholder substitution.  Templates are cached in memory
after first load to avoid repeated file I/O.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


class PromptLoader:
    """Load and interpolate prompt templates from the filesystem.

    Templates are plain ``.txt`` files stored under ``prompts_dir``.  Variables
    are replaced using Python's ``str.format()``-style ``{key}`` syntax.

    Attributes
    ----------
    prompts_dir : Path
        Absolute path to the directory containing ``.txt`` prompt templates.

    Examples
    --------
    >>> loader = PromptLoader()
    >>> prompt = loader.render("title", product_name="太阳镜", features="偏光", category="配饰")
    """

    # ------------------------------------------------------------------
    def __init__(self, prompts_dir: Optional[str] = None) -> None:
        """Initialise the loader and set the prompts directory.

        Parameters
        ----------
        prompts_dir : str, optional
            Path to the prompts directory.  Defaults to ``ai_service/prompts/``
            relative to the project root.
        """
        if prompts_dir is None:
            # Resolve relative to *this file's* parent directory → ai_service root
            root = Path(__file__).resolve().parent.parent
            prompts_dir = str(root / "prompts")

        self.prompts_dir = Path(prompts_dir)
        if not self.prompts_dir.is_dir():
            raise FileNotFoundError(
                f"Prompts directory not found: {self.prompts_dir}"
            )

        # Simple in-memory cache: template_name → raw template string
        self._cache: Dict[str, str] = {}

    # ------------------------------------------------------------------
    def load(self, template_name: str) -> str:
        """Load a raw template by name (without extension).

        Parameters
        ----------
        template_name : str
            Name of the template file *without* the ``.txt`` extension
            (e.g. ``"title"`` loads ``title.txt``).

        Returns
        -------
        str
            Raw template content (with ``{placeholders}`` intact).

        Raises
        ------
        FileNotFoundError
            If the template file does not exist.
        """
        if template_name in self._cache:
            return self._cache[template_name]

        file_path = self.prompts_dir / f"{template_name}.txt"
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Prompt template not found: {file_path}"
            )

        content = file_path.read_text(encoding="utf-8")
        self._cache[template_name] = content
        return content

    # ------------------------------------------------------------------
    def render(self, template_name: str, **kwargs: Any) -> str:
        """Load a template and substitute variables.

        Parameters
        ----------
        template_name : str
            Template name without extension.
        **kwargs
            Key-value pairs used to fill ``{placeholders}`` in the template.

        Returns
        -------
        str
            Rendered prompt string ready to be sent to the LLM.

        Raises
        ------
        KeyError
            If a placeholder in the template was not provided in ``**kwargs``.
        FileNotFoundError
            If the template file does not exist.
        """
        raw = self.load(template_name)
        try:
            return raw.format(**kwargs)
        except KeyError as exc:
            raise KeyError(
                f"Missing variable {exc} for template '{template_name}'"
            ) from exc

    # ------------------------------------------------------------------
    def clear_cache(self) -> None:
        """Clear the internal template cache.

        Useful during development when templates are edited on disk and
        you want to force a reload without restarting the process.
        """
        self._cache.clear()

    # ------------------------------------------------------------------
    def list_templates(self) -> list[str]:
        """Return a sorted list of available template names (without extension).

        Returns
        -------
        list[str]
            Template names that can be passed to :meth:`load` or :meth:`render`.
        """
        return sorted(
            p.stem for p in self.prompts_dir.glob("*.txt")
        )
