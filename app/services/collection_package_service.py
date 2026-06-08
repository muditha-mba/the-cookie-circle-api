"""Collection package business logic."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.collection_package import CollectionPackage
from app.repositories.collection_package_repository import CollectionPackageRepository
from app.schemas.collection_package import (
    CollectionPackageCreate,
    CollectionPackageResponse,
    CollectionPackageUpdate,
)
from app.schemas.pagination import PaginatedResponse, PaginationParams


class CollectionPackageService:
    """Handles collection package CRUD operations."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.packages = CollectionPackageRepository(db)

    def create(self, payload: CollectionPackageCreate) -> CollectionPackageResponse:
        if self.packages.get_by_code(payload.code):
            raise ConflictError("A collection package with this code already exists")
        if self.packages.get_by_name(payload.name):
            raise ConflictError("A collection package with this name already exists")

        package = CollectionPackage(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            badge_tone=payload.badge_tone,
            is_active=payload.is_active,
        )
        self.packages.create(package)
        self.db.commit()
        self.db.refresh(package)
        return CollectionPackageResponse.model_validate(package)

    def get(self, package_id: uuid.UUID) -> CollectionPackageResponse:
        package = self.packages.get_by_id(package_id)
        if not package:
            raise NotFoundError("Collection package not found")
        return CollectionPackageResponse.model_validate(package)

    def list(self, params: PaginationParams) -> PaginatedResponse[CollectionPackageResponse]:
        items, total = self.packages.list_paginated(
            page=params.page,
            page_size=params.page_size,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return PaginatedResponse(
            items=[CollectionPackageResponse.model_validate(item) for item in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=self.packages.total_pages(total, params.page_size),
        )

    def update(self, package_id: uuid.UUID, payload: CollectionPackageUpdate) -> CollectionPackageResponse:
        package = self.packages.get_by_id(package_id)
        if not package:
            raise NotFoundError("Collection package not found")

        if payload.code is not None:
            existing_code = self.packages.get_by_code(payload.code)
            if existing_code and existing_code.id != package.id:
                raise ConflictError("A collection package with this code already exists")
            package.code = payload.code

        if payload.name is not None:
            existing_name = self.packages.get_by_name(payload.name)
            if existing_name and existing_name.id != package.id:
                raise ConflictError("A collection package with this name already exists")
            package.name = payload.name

        if payload.description is not None:
            package.description = payload.description
        if payload.badge_tone is not None:
            package.badge_tone = payload.badge_tone
        if payload.is_active is not None:
            package.is_active = payload.is_active

        self.db.add(package)
        self.db.commit()
        self.db.refresh(package)
        return CollectionPackageResponse.model_validate(package)

    def delete(self, package_id: uuid.UUID) -> None:
        package = self.packages.get_by_id(package_id)
        if not package:
            raise NotFoundError("Collection package not found")
        if self.packages.count_collections_for_package(package_id) > 0:
            raise ValidationError(
                "Cannot delete a package that is assigned to existing collections",
            )
        self.packages.delete(package)
        self.db.commit()
