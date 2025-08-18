"""Defines controller"""

from fastapi import APIRouter


class RestController:
    """Implements a base REST controller"""

    def prepare(self, app: APIRouter) -> None:
        """Prepares the service"""
