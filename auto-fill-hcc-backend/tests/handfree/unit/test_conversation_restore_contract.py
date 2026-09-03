from app.channels.handfree.chat import flow, router, store


def test_restore_refreshes_execution_subject_inside_existing_location_card():
    conv = store.new_conversation()
    conv["last_reply"] = {
        "display_md": "Xin chào",
        "tts_text": "Xin chào",
        "chips": [],
        "cards": [flow._location_card(conv)],  # noqa: SLF001
        "state": "greet",
    }

    reply = flow._apply_execution_subject(  # noqa: SLF001
        conv,
        {"key": "authorized_person"},
    )
    assert reply.display_md == ""

    restored = router._last_reply_for_restore(conv)  # noqa: SLF001
    assert restored["cards"][0]["executionSubject"]["current"] == "authorized_person"
    assert conv["last_reply"]["cards"][0]["executionSubject"]["current"] == "self"


def test_restore_refreshes_docs_done_label_from_latest_page_target():
    conv = store.new_conversation()
    conv["docs_target"] = "attachment"
    conv["last_reply"] = {
        "display_md": "Công dân gửi giấy tờ giúp em ạ.",
        "tts_text": "",
        "chips": [
            {
                "label": "✅ Đã đưa đủ giấy tờ, xử lý đi",
                "send": "__action:docs_done",
                "solid": True,
            }
        ],
        "cards": [],
        "state": "collecting_docs",
    }

    restored = router._last_reply_for_restore(conv)  # noqa: SLF001

    assert restored["chips"][0]["label"] == "✅ Đã đưa đủ giấy tờ, đính kèm đi"
    assert conv["last_reply"]["chips"][0]["label"] == "✅ Đã đưa đủ giấy tờ, xử lý đi"


def test_restore_keeps_declaration_adjustment_target_after_sidebar_reload():
    conv = store.new_conversation()
    conv.update({
        "docs_target": "declaration",
        "supplementing_documents": True,
        "supplement_reuse_session": True,
        "documents_adjustment_target": "declaration",
        "last_reply": {
            "display_md": "Công dân điều chỉnh giấy tờ giúp em ạ.",
            "tts_text": "",
            "chips": [{
                "label": "✅ Hoàn tất điều chỉnh, đính kèm lại",
                "send": "__action:docs_done",
                "solid": True,
            }],
            "cards": [],
            "state": "collecting_docs",
        },
    })

    restored = router._last_reply_for_restore(conv)  # noqa: SLF001

    assert restored["chips"][0]["label"] == "✅ Hoàn tất điều chỉnh, điền lại tờ khai"
