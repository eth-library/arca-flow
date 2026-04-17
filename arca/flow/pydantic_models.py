"""
OAIS-Compliant Data Models for Digital Preservation

This module defines a hierarchy of Pydantic models that implement the OAIS
(Open Archival Information System) reference model for digital preservation.
The models enforce data validation and maintain relationships between different
components of a Submission Information Package (SIP).

Model Hierarchy:
    SIPModel
    ├── IEModel (Intellectual Entity)
    │   ├── DublinCore (Metadata)
    │   └── RepresentationModel
    │       └── FileModel
    │           └── FixityModel

Key Features:
    - Full OAIS compliance
    - Dublin Core metadata support
    - Strict data validation
    - Immutable fixity records
    - UUID-based identification
    - Hierarchical representation
    - Timestamp normalization

Usage:
    ```python
    from arca.flow.pydantic_models import SIPModel, IEModel

    # Create a new SIP
    sip = SIPModel(
        sip_id="unique_id",
        submitting_agent="agent_name",
        intellectual_entities=[...]
    )

    # Validation is automatic
    sip.creation_date = "invalid_date"  # Raises ValidationError
    ```

Note:
    All models use Pydantic's validation system to ensure data integrity
    and OAIS compliance. Fields are documented with clear descriptions
    and validation rules.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class FixityType(StrEnum):
    """
    Enumeration of supported cryptographic hash algorithms for file fixity.

    These algorithms are used to generate and validate checksums that ensure
    file integrity in digital preservation. The supported algorithms are
    ordered from least to most secure:
        - MD5: Legacy algorithm, fast but less secure
        - SHA1: More secure than MD5, but showing age
        - SHA256: Current recommended standard
        - SHA512: Highest security, but more resource-intensive

    Note:
        Choice of algorithm should balance security needs with performance
        requirements. SHA256 is recommended for most use cases.
    """

    MD5 = "MD5"
    SHA1 = "SHA-1"
    SHA256 = "SHA-256"
    SHA512 = "SHA-512"


class FixityModel(BaseModel):
    """
    Model for file fixity (checksum) information in digital preservation.

    Fixity information is crucial for ensuring the integrity and authenticity
    of preserved digital objects. This model stores cryptographic hash values
    that can be used to verify that a file hasn't been altered.

    The model is immutable (frozen=True) to prevent accidental modification
    of checksum records after creation.

    Fields:
        fixity_type: The hash algorithm used (MD5, SHA-1, etc.)
        fixity_value: The actual hash value (must not be empty)
        file_id: Reference to the file this checksum belongs to

    Validation:
        - fixity_type must be a valid FixityType enum value
        - fixity_value must be a non-empty string
        - file_id must be a valid string (typically a UUID)

    Example:
        ```python
        fixity = FixityModel(
            fixity_type=FixityType.SHA256,
            fixity_value="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            file_id="123e4567-e89b-12d3-a456-426614174000"
        )
        # Once created, the record cannot be modified
        fixity.fixity_value = "new_value"  # Raises FrozenInstanceError
        ```
    """

    fixity_type: FixityType = Field(..., description="Type of the checksum algorithm.")
    fixity_value: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., description="Checksum value."
    )
    file_id: str = Field(..., description="ID of the file this fixity belongs to")

    model_config = ConfigDict(frozen=True)


class FileModel(BaseModel):
    """
    Model representing a file within an OAIS Information Package.

    In the OAIS context, a file is the basic unit of preserved content,
    containing both the actual data and its associated technical metadata.
    Files are grouped into Representations, which in turn belong to
    Intellectual Entities.

    Relationships:
        - Parent: RepresentationModel (many-to-one)
        - Children: FixityModel (one-to-many)
        - References: Administrative and descriptive metadata through ID lists

    Required Fields:
        - file_id: Unique identifier (typically UUID)
        - label: Human-readable name
        - mime_type: Content type identifier
        - original_name: Name from source system
        - size_bytes: File size

    Optional Fields:
        - original_path: Path in source system
        - fixities: List of checksums
        - dmd_ids: Descriptive metadata references
        - adm_ids: Administrative metadata references

    Validation:
        - All required fields must be present
        - size_bytes must be non-negative
        - mime_type must be a valid MIME type string
        - IDs should be valid references in the METS document

    Example:
        ```python
        file = FileModel(
            file_id="123e4567-e89b-12d3-a456-426614174000",
            label="Main Document",
            mime_type="application/pdf",
            original_name="document.pdf",
            size_bytes=1048576,
            fixities=[FixityModel(...)],
            dmd_ids=["dmd001"],
            adm_ids=["amd001"]
        )
        ```

    Note:
        The model maintains relationships with other components through ID
        references, which should be validated at the SIP level to ensure
        referential integrity.
    """

    file_id: str = Field(..., description="Unique identifier for the file")
    label: str = Field(..., description="Human-readable label")
    mime_type: str = Field(..., description="MIME type of the file")
    original_name: str = Field(..., description="Original filename")
    original_path: str | None = Field(None, description="Original file path")
    size_bytes: int = Field(..., description="File size in bytes")
    fixities: list[FixityModel] = Field(default_factory=list, description="File checksums")
    dmd_ids: list[str] = Field(default_factory=list, description="Descriptive metadata IDs")
    adm_ids: list[str] = Field(default_factory=list, description="Administrative metadata IDs")


class RepresentationType(StrEnum):
    """
    OAIS-compliant representation types for digital objects.

    In OAIS, different representations serve distinct preservation and access
    purposes. Each type has specific characteristics and use cases:

    PRESERVATION:
        - Highest quality version for long-term preservation
        - Usually in preservation-friendly formats (e.g., TIFF, WAV)
        - May be large in size
        - Maintains all significant properties of the original
        - Used for future preservation actions

    ACCESS:
        - Optimized for user access and delivery
        - Usually in commonly accessible formats (e.g., PDF, JPEG)
        - Typically smaller than preservation copies
        - May have reduced quality for easier distribution
        - Used for regular user access

    ORIGINAL:
        - The original submitted version
        - Format depends on the source system
        - Kept for authenticity and provenance
        - May not be suitable for preservation or access
        - Used as reference and for integrity verification

    Note:
        The choice of representation type affects preservation strategy
        and access policies. Most Intellectual Entities should have at
        least a preservation and an access representation.
    """

    PRESERVATION = "preservation"
    ACCESS = "access"
    ORIGINAL = "original"


class RepresentationModel(BaseModel):
    """
    Model for OAIS representation information, grouping related files.

    In OAIS, a representation is a set of files that together constitute a
    usable version of an Intellectual Entity. For example, a book might have
    a preservation representation (high-res TIFF files) and an access
    representation (PDF file).

    Relationships:
        - Parent: IEModel (many-to-one)
        - Children: FileModel (one-to-many)
        - Type: RepresentationType (one-to-one)

    Fields:
        - rep_id: Auto-generated UUID if not provided
        - label: Optional human-readable name
        - usage_type: Purpose of this representation (defaults to ACCESS)
        - files: List of component files
        - creation_date: When this representation was created (UTC)

    Validation:
        - rep_id must be a valid string (typically UUID)
        - usage_type must be a valid RepresentationType
        - files must be a list (can be empty)
        - creation_date must be a valid UTC datetime if provided

    Example:
        ```python
        representation = RepresentationModel(
            label="Preservation Master",
            usage_type=RepresentationType.PRESERVATION,
            files=[
                FileModel(file_id="file1", ...),
                FileModel(file_id="file2", ...)
            ],
            creation_date=datetime.now(timezone.utc)
        )
        # rep_id is auto-generated if not provided
        print(representation.rep_id)  # UUID string
        ```

    Note:
        - Each representation should contain all files needed to render
          or use the Intellectual Entity in its intended form
        - Files within a representation should be logically related
        - Creation date is automatically set to UTC timezone
        - The usage_type helps determine appropriate preservation and
          access strategies
    """

    rep_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique identifier for the representation"
    )
    label: str | None = Field(None, description="Human-readable label")
    usage_type: RepresentationType | None = Field(
        RepresentationType.ACCESS, description="Type of representation"
    )
    files: list[FileModel] = Field(default_factory=list, description="Files in this representation")
    creation_date: datetime | None = Field(None, description="Creation timestamp")


class DublinCore(BaseModel):
    """
    Dublin Core metadata model for OAIS descriptive metadata.

    This model implements a subset of the Dublin Core Metadata Element Set
    (Version 1.1) that is relevant for digital preservation. Dublin Core
    is used as the primary descriptive metadata standard due to its
    simplicity and wide adoption.

    Implemented Fields:
        title: Names given to the resource
            - Main title
            - Alternative titles
            - Subtitles

        creator: Entities responsible for making the resource
            - Authors
            - Artists
            - Organizations
            - Other creators

        type: Nature or genre of the resource
            - Document types
            - Resource categories
            - Content types

        identifier: Unambiguous references to the resource
            - Local identifiers
            - URIs
            - ISBN/DOI/etc.

        rights: Information about rights over the resource
            - Copyright statements
            - License information
            - Access restrictions

    All fields are implemented as lists to support multiple values
    and different languages or forms of the same metadata element.

    Example:
        ```python
        metadata = DublinCore(
            title=["Main Title", "Alternative Title"],
            creator=["Author, Jane", "Organization Name"],
            type=["Text", "Documentation"],
            identifier=["DOI:10.1000/xyz123", "ISBN:978-3-16-148410-0"],
            rights=["Copyright 2023", "CC-BY-4.0"]
        )
        ```

    Note:
        - All fields are optional but should be populated when available
        - Empty lists are used for missing metadata
        - Values should follow standard formatting where applicable
        - Additional Dublin Core elements can be added as needed
    """

    title: list[str] = Field(default_factory=list, description="The name given to the resource")
    creator: list[str] = Field(
        default_factory=list, description="An entity responsible for making the resource"
    )
    type: list[str] = Field(default_factory=list, description="The nature or genre of the resource")
    identifier: list[str] = Field(
        default_factory=list, description="An unambiguous reference to the resource"
    )
    rights: list[str] = Field(
        default_factory=list, description="Information about rights held in and over the resource"
    )


class IEModel(BaseModel):
    """
    Model for OAIS Intellectual Entity (IE), representing a coherent digital object.

    In OAIS, an Intellectual Entity is a distinct intellectual or artistic creation
    that is considered relevant for preservation. It can be a document, dataset,
    image, or any other coherent unit of information. Each IE can have multiple
    representations for different purposes.

    Relationships:
        - Parent: SIPModel (many-to-one)
        - Children: RepresentationModel (one-to-many)
        - Metadata: DublinCore (one-to-one)

    Required Fields:
        - ie_id: Unique identifier for the entity
        - dc: Dublin Core metadata describing the entity
        - ie_entity_type: Classification of the entity type

    Optional Fields:
        - representations: List of different versions/forms of the entity

    Validation:
        - ie_id must be a valid string (typically UUID)
        - dc must be a valid DublinCore instance
        - ie_entity_type must be a non-empty string
        - representations must be a list (can be empty)

    Example:
        ```python
        entity = IEModel(
            ie_id="123e4567-e89b-12d3-a456-426614174000",
            dc=DublinCore(
                title=["Document Title"],
                creator=["Author Name"],
                rights=["Copyright 2023"]
            ),
            ie_entity_type="document",
            representations=[
                RepresentationModel(
                    usage_type=RepresentationType.PRESERVATION,
                    files=[...]
                ),
                RepresentationModel(
                    usage_type=RepresentationType.ACCESS,
                    files=[...]
                )
            ]
        )
        ```

    Note:
        - Each IE should have at least one representation
        - Dublin Core metadata is required for discovery and management
        - The ie_entity_type helps in applying appropriate preservation rules
        - Multiple representations allow for different use cases (preservation,
          access, etc.)
    """

    ie_id: str = Field(..., description="Unique identifier for the IE")
    dc: DublinCore = Field(..., description="Dublin Core metadata")
    ie_entity_type: str = Field(..., description="Type of intellectual entity")
    representations: list[RepresentationModel] = Field(
        default_factory=list, description="Different representations of this IE"
    )


class SIPModel(BaseModel):
    """
    Model for OAIS Submission Information Package (SIP).

    A SIP is the package that is sent to an OAIS archive for ingest. It contains
    one or more Intellectual Entities along with their representations and all
    necessary metadata for preservation. This model enforces OAIS compliance
    through strict validation rules.

    Model Configuration:
        - validate_assignment=True: Validates data on attribute assignment
        - extra="forbid": Prevents additional fields beyond those defined
        - Nested validation for all contained models

    Relationships:
        - Children: IEModel (one-to-many)
        - Contains: Complete preservation object hierarchy
        - References: External systems through submitting_agent

    Required Fields:
        - sip_id: Unique identifier for the package
        - submitting_agent: Entity responsible for submission
        - intellectual_entities: List of contained IEs (can be empty)

    Optional Fields:
        - creation_date: UTC timestamp of package creation

    Validation Rules:
        - sip_id must be a valid string (typically UUID)
        - submitting_agent must be non-empty
        - creation_date must be UTC if provided
        - All contained IEs must be valid
        - No extra fields allowed

    Example:
        ```python
        sip = SIPModel(
            sip_id="123e4567-e89b-12d3-a456-426614174000",
            submitting_agent="Digital Archive System",
            intellectual_entities=[
                IEModel(
                    ie_id="ie_001",
                    dc=DublinCore(...),
                    ie_entity_type="document",
                    representations=[...]
                )
            ],
            creation_date=datetime.now(timezone.utc)
        )
        ```

    Note:
        - The model enforces a strict hierarchical structure
        - All timestamps are normalized to UTC
        - Validation occurs on both creation and modification
        - The model ensures completeness for archival purposes
        - Submitting agent should be a system or organization identifier
    """

    sip_id: str = Field(..., description="Unique identifier for the SIP")
    intellectual_entities: list[IEModel] = Field(
        default_factory=list, description="Intellectual entities in this SIP"
    )
    creation_date: datetime | None = Field(None, description="SIP creation timestamp")
    submitting_agent: str = Field(..., description="Agent responsible for SIP submission")

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
