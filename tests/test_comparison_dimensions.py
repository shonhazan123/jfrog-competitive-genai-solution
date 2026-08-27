def test_five_dimensions_with_positions():
    from app.services.comparison_matrix import load_dimensions

    dims = load_dimensions()
    assert [d["key"] for d in dims] == [
        "artifact_management",
        "sca_sbom",
        "container_security",
        "cicd_integration",
        "developer_experience",
    ]
    assert all(d["jfrog_position"] for d in dims)          # every column has a yardstick
    assert all(d["probe_keywords"] for d in dims)
