"""
Hypothesis Configuration for Property-Based Testing

This module configures Hypothesis settings for all property-based tests.
"""

from hypothesis import settings, Verbosity, Phase
import os


# Define profiles for different testing scenarios
settings.register_profile(
    "default",
    max_examples=50,
    deadline=5000,  # 5 seconds per test
    stateful_step_count=10,
    verbosity=Verbosity.normal,
    print_blob=False,
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.target, Phase.shrink],
)

settings.register_profile(
    "ci",
    max_examples=100,
    deadline=10000,  # 10 seconds per test in CI
    stateful_step_count=20,
    verbosity=Verbosity.normal,
    print_blob=True,
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.target, Phase.shrink],
)

settings.register_profile(
    "dev",
    max_examples=20,
    deadline=2000,  # 2 seconds for quick feedback
    stateful_step_count=5,
    verbosity=Verbosity.verbose,
    print_blob=True,
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.target],
)

settings.register_profile(
    "debug",
    max_examples=10,
    deadline=None,  # No deadline for debugging
    stateful_step_count=5,
    verbosity=Verbosity.debug,
    print_blob=True,
    phases=[Phase.explicit, Phase.reuse, Phase.generate],
)

settings.register_profile(
    "thorough",
    max_examples=500,
    deadline=30000,  # 30 seconds for thorough testing
    stateful_step_count=50,
    verbosity=Verbosity.normal,
    print_blob=True,
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.target, Phase.shrink],
)

# Load profile based on environment variable
profile = os.getenv("HYPOTHESIS_PROFILE", "default")
settings.load_profile(profile)

# Export settings for use in tests
__all__ = ["settings"]
