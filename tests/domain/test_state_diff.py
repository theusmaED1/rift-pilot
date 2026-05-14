"""Testes das propriedades de `StateDiff`."""


def test_player_leveled_up_detects_level_change(make_state, make_diff):
    diff = make_diff(
        previous=make_state(player_level=5),
        current=make_state(player_level=6),
    )
    assert diff.player_leveled_up is True


def test_available_skill_points_accounts_for_unspent_levels(make_state, make_diff):
    diff = make_diff(
        previous=make_state(player_level=1, q=1),
        current=make_state(player_level=3, q=1),
    )
    assert diff.available_skill_points == 2


def test_items_changed_detects_purchase(make_state, make_diff):
    diff = make_diff(
        previous=make_state(owned_item_ids=()),
        current=make_state(owned_item_ids=(1001,)),
    )
    assert diff.items_changed is True


def test_new_events_returns_only_unseen_ids(make_state, make_diff, make_game_event):
    seen_event = make_game_event(event_id=1, name="MinionsSpawning")
    fresh_event = make_game_event(event_id=2, name="DragonKill", time_seconds=320.0)
    diff = make_diff(
        previous=make_state(events=[seen_event]),
        current=make_state(events=[seen_event, fresh_event]),
    )
    assert [event.event_id for event in diff.new_events] == [2]
