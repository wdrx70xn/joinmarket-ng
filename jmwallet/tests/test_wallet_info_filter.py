"""Tests for empty-address filtering in `jm-wallet info --extended`.

Issue: after running a wallet for a few months, the extended view becomes
unreadable because most addresses have zero balance. This test exercises
the `_print_branch_addresses` helper that drives the filtering.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout

from jmwallet.cli.wallet import _print_branch_addresses
from jmwallet.wallet.models import AddressInfo


def _mk(index: int, status: str, balance: int, branch: int = 0) -> AddressInfo:
    return AddressInfo(
        address=f"bc1qaddr{index:04d}",
        index=index,
        balance=balance,
        status=status,  # type: ignore[arg-type]
        path=f"m/84'/0'/0'/{branch}/{index}",
        is_external=(branch == 0),
    )


def _capture(addresses: list[AddressInfo], show_empty: bool) -> tuple[str, int, int]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        total, hidden = _print_branch_addresses(
            addresses,
            pending_addresses=set(),
            frozen_addresses=set(),
            show_empty=show_empty,
        )
    return buf.getvalue(), total, hidden


class TestPrintBranchAddressesFiltering:
    def test_show_empty_true_prints_every_address(self) -> None:
        addrs = [
            _mk(0, "used-empty", 0),
            _mk(1, "deposit", 100_000),
            _mk(2, "new", 0),
            _mk(3, "new", 0),
        ]
        output, total, hidden = _capture(addrs, show_empty=True)

        # Every address must appear; nothing hidden.
        for a in addrs:
            assert a.address in output
        assert hidden == 0
        assert total == 100_000

    def test_show_empty_false_hides_zero_balance_entries(self) -> None:
        addrs = [
            _mk(0, "used-empty", 0),
            _mk(1, "deposit", 100_000),
            _mk(2, "used-empty", 0),
            _mk(3, "new", 0),  # kept: first "new" address
            _mk(4, "new", 0),  # kept: within new_address_limit (default 6)
        ]
        output, total, hidden = _capture(addrs, show_empty=False)

        # Non-empty address is always shown.
        assert "bc1qaddr0001" in output
        # Both "new" receive addresses are surfaced up to the default
        # limit of 6 so users can pick multiple fresh deposit addresses
        # without having to drop to --show-empty (issue #463).
        assert "bc1qaddr0003" in output
        assert "bc1qaddr0004" in output
        # Zero-balance used-empty/flagged lines are dropped.
        assert "bc1qaddr0000" not in output
        assert "bc1qaddr0002" not in output

        # 2 entries hidden (used-empty at 0 and 2); balance still totals everything.
        assert hidden == 2
        assert total == 100_000

    def test_show_empty_false_with_no_new_address_still_shows_funded_only(self) -> None:
        """If no 'new' address exists (all used), don't invent one; only print funded ones."""
        addrs = [
            _mk(0, "used-empty", 0),
            _mk(1, "deposit", 42),
            _mk(2, "used-empty", 0),
        ]
        output, total, hidden = _capture(addrs, show_empty=False)

        assert "bc1qaddr0001" in output
        assert "bc1qaddr0000" not in output
        assert "bc1qaddr0002" not in output
        assert hidden == 2
        assert total == 42

    def test_balance_accounts_for_hidden_addresses(self) -> None:
        """Total balance must include addresses even if we skipped printing them."""
        # Corner case: a funded address still gets printed; the balance
        # sum must be correct regardless of show_empty.
        addrs = [
            _mk(0, "used-empty", 0),
            _mk(1, "deposit", 10),
            _mk(2, "cj-out", 20),
            _mk(3, "new", 0),
        ]
        _, total_shown, _ = _capture(addrs, show_empty=True)
        _, total_hidden, _ = _capture(addrs, show_empty=False)
        assert total_shown == total_hidden == 30

    def test_multiple_new_addresses_shown_up_to_default_limit(self) -> None:
        """Issue #463: show up to 6 empty 'new' addresses so users can send
        multiple deposits without enabling --show-empty (which would also
        surface confusing used-empty/flagged lines)."""
        addrs = [_mk(i, "new", 0) for i in range(10)]
        output, _, hidden = _capture(addrs, show_empty=False)

        # First 6 "new" addresses are shown, the rest are hidden.
        for i in range(6):
            assert f"bc1qaddr{i:04d}" in output
        for i in range(6, 10):
            assert f"bc1qaddr{i:04d}" not in output
        assert hidden == 4

    def test_used_empty_and_flagged_are_always_hidden_in_default_view(self) -> None:
        """Issue #463: used-empty and flagged addresses (both unsafe to
        reuse) must never appear in the default view -- not even as the
        leading placeholder -- so the output stays actionable."""
        addrs = [
            _mk(0, "used-empty", 0),
            _mk(1, "flagged", 0),
            _mk(2, "deposit", 500),
            _mk(3, "new", 0),
        ]
        output, total, hidden = _capture(addrs, show_empty=False)

        assert "bc1qaddr0000" not in output  # used-empty suppressed
        assert "bc1qaddr0001" not in output  # flagged suppressed
        assert "bc1qaddr0002" in output  # funded deposit is shown
        assert "bc1qaddr0003" in output  # fresh "new" is shown
        # Both unsafe-to-reuse entries counted as hidden.
        assert hidden == 2
        assert total == 500

    def test_show_empty_true_still_prints_used_empty_and_flagged(self) -> None:
        """Power users running `jm-wallet info --extended --show-empty`
        must still see the full picture (issue #463)."""
        addrs = [
            _mk(0, "used-empty", 0),
            _mk(1, "flagged", 0),
            _mk(2, "new", 0),
        ]
        output, _, hidden = _capture(addrs, show_empty=True)

        assert "bc1qaddr0000" in output
        assert "bc1qaddr0001" in output
        assert "bc1qaddr0002" in output
        assert hidden == 0
