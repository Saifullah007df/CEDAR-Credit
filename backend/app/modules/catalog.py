"""Phase 1 implementation inventory; deliberately no credit-scoring data."""

from app.api.schemas import ArchitectureLayer, Capability, CapabilityStatus

CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        id="foundation",
        title="Application Foundation",
        phase=1,
        status=CapabilityStatus.IMPLEMENTED,
        description="React navigation and a live FastAPI informational API.",
    ),
    Capability(
        id="identity",
        title="Authentication & Consent",
        phase=2,
        status=CapabilityStatus.PLANNED,
        description="Server-enforced roles and authorized borrower-data access.",
    ),
    Capability(
        id="applications",
        title="Applications & Lender Catalog",
        phase=3,
        status=CapabilityStatus.PLANNED,
        description="Persist borrower applications and simulated lender products.",
    ),
    Capability(
        id="rg03",
        title="RG-03 · Explainable Lending Rules",
        phase=4,
        status=CapabilityStatus.PLANNED,
        description="Versioned lender policies with executed-rule explanations.",
    ),
    Capability(
        id="rg02",
        title="RG-02 · Multilingual Evidence Registry",
        phase=5,
        status=CapabilityStatus.PLANNED,
        description="Source-linked candidate facts and documented uncertainty.",
    ),
    Capability(
        id="dependency",
        title="CEDAR · Counterfactual Dependency Engine",
        phase=6,
        status=CapabilityStatus.PLANNED,
        description="Evidence-to-rule dependencies and decision stability checks.",
    ),
    Capability(
        id="rg09",
        title="RG-09 · Adaptive Human Review",
        phase=7,
        status=CapabilityStatus.PLANNED,
        description="Risk-sensitive review and selective re-evaluation.",
    ),
    Capability(
        id="lifecycle",
        title="Offer & Loan Lifecycle",
        phase=8,
        status=CapabilityStatus.PLANNED,
        description="Simulated agreements, disbursement and repayments.",
    ),
    Capability(
        id="rg04",
        title="RG-04 · Utilization Evidence",
        phase=9,
        status=CapabilityStatus.PLANNED,
        description="Reviewable purpose-to-expenditure evidence links.",
    ),
    Capability(
        id="verification",
        title="Integrated Verification",
        phase=10,
        status=CapabilityStatus.PLANNED,
        description="Regression, authorization and algorithm correctness testing.",
    ),
)

ARCHITECTURE_LAYERS: tuple[ArchitectureLayer, ...] = (
    ArchitectureLayer(
        name="Presentation",
        modules=["Borrower Portal", "Lender Portal", "Admin Portal", "Review Workspace"],
        status=CapabilityStatus.IMPLEMENTED,
    ),
    ArchitectureLayer(
        name="Application Services",
        modules=["Applications", "Lender Catalog", "Loan Lifecycle", "Authentication"],
        status=CapabilityStatus.PLANNED,
    ),
    ArchitectureLayer(
        name="CEDAR Research",
        modules=[
            "RG-02 Evidence Registry", "Evidence Dependency Graph", "RG-03 Rules Engine",
            "Counterfactual Analyzer", "RG-09 Review Scheduler", "Selective Re-evaluation",
            "RG-04 Utilization Verification",
        ],
        status=CapabilityStatus.PLANNED,
    ),
    ArchitectureLayer(
        name="Persistence & Integrations",
        modules=["PostgreSQL", "Private Document Storage", "Mock Lender & Payment APIs"],
        status=CapabilityStatus.PLANNED,
    ),
)
