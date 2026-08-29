def test_reporter_writes_human_label_and_counter():
    from app.models.run import create_run, get_run
    from app.controllers.runs import make_reporter
    run = create_run()
    report = make_reporter(run.id, "comparison")
    report("research", current=12, total=30)
    r = get_run(run.id)
    assert r.step_label == "Researching each rival's strengths"
    assert r.step_detail == "12 of 30"
    assert r.current == 12 and r.total == 30


def test_reporter_without_counter_has_no_detail():
    from app.models.run import create_run, get_run
    from app.controllers.runs import make_reporter
    run = create_run()
    make_reporter(run.id, "industry")("plan")
    assert get_run(run.id).step_label == "Deciding what to look into"
    assert get_run(run.id).step_detail is None
