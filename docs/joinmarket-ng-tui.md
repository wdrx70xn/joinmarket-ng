

# JoinMarket-NG TUI Menu Documentation

The JoinMarket-NG TUI is a minimalistic, security-focused Linux environment for **JoinMarket-NG** with a terminal-based graphical menu interface. It's a user-friendly wrapper around the JoinMarket-NG software. The TUI provides an accessible way to use coinjoin technology for Bitcoin privacy features without memorizing CLI commands.


The menu can be accessed by running `./menu.sh`.

---

## Main Menu

![Main Menu](./media/main-menu.png)

The main menu provides access to all JoinMarket-NG operations. The header shows the current active wallet and maker service status.

| Option | Description |
|--------|-------------|
| **S** | Send Bitcoin (normal transaction or CoinJoin) |
| **W** | Wallet Management |
| **M** | Maker Bot Control |
| **C** | Edit Configuration (`config.toml`) |
| **I** | Info / Documentation |
| **X** | Exit |

---

## Send Bitcoin (Input Screen)

![Send Input](./media/send-bitcoin-input.png)

Configure your Bitcoin send parameters. Set the number of counterparties to **0** for a normal transaction or **4–10** for a CoinJoin. The display shows current values as you input each parameter.

| Parameter | Description |
|-----------|-------------|
| **Mixdepth** | Source account (mixdepth) to send from |
| **Amount** | Satoshis to send (0 = sweep entire mixdepth) |
| **Counterparties** | Number of makers (0 = normal, >0 = CoinJoin) |
| **Fee Rate** | Fee Rate in sats/vB (leave blank for auto-estimate) |
| **Destination** | Bitcoin address or "INTERNAL" for CoinJoin sweep |

---

## Wallet Management

![Wallet Management](./media/wallet-management-menu.png)

Manage your wallets through this submenu. This section contains all tools to manage your Bitcoin wallet easily and securely. Generate new wallets or select your active wallet. Validate seed words and import (restore) existing wallets. Check wallet balances and CoinJoin transaction history. Use coin control features to freeze specific coins and manage UTXOs efficiently. 

| Option | Description |
|--------|-------------|
| **NEW** | Create a new wallet with a 24-word BIP39 seed |
| **IMP** | Import an existing wallet (12 or 24 words) |
| **VAL** | Validate a seed phrase before importing |
| **BAL** | View wallet info / balance |
| **HIST** | Display CoinJoin transaction history |
| **FREEZE** | Freeze or unfreeze individual UTXOs |
| **SEL** | Select the active wallet from available wallets |
| **BACK** | Return to the main menu |

---

## Wallet Info (Balance View)

![Wallet Info](./media/wallet-info-menu.png)

The Balance submenu offers two display levels to suit different needs. Choose between a quick overview or detailed breakdown.

| Option | Description |
|--------|-------------|
| **BASIC** | Quick balance summary by mixdepth (account) |
| **EXT** | Extended view with detailed address list and status labels |
| **BACK** | Return to Wallet Management |

**BASIC view** shows:

- Total balance across all mixdepths
- Individual balance per mixdepth

**EXTENDED view** shows:

- All external and internal addresses with their derivation paths
- Status labels: `new`, `deposit`, `cj-out`, `non-cj-change`, `used-empty`, `flagged`
- Individual address balances
- Mixdepth totals

This allows users to quickly check funds or investigate specific address statuses for privacy analysis.

---

## Maker Bot Control

![Maker Bot Control](./media/maker-menu.png)

Control the JoinMarket-NG maker bot service. As a Maker, you advertise your coins on the JoinMarket network for use in coinjoins. When a Taker selects your offer, your coins are included in the transaction and you earn a small fee in Satoshis. Run this as a background service to earn passive income while improving your privacy.

| Option | Description |
|--------|-------------|
| **START** | Start the maker service |
| **STOP** | Stop the maker service |
| **RESTART** | Restart the maker service |
| **BONDS** | Manage Fidelity Bonds (boost maker reputation) |
| **LOG** | Follow maker logs in real-time (Ctrl+C to stop) |
| **STATUS** | Display current service status |
| **BACK** | Return to the main menu |

---

## Fidelity Bonds

![Fidelity Bonds](./media/fidelity-bond-menu.png)

Fidelity bonds lock coins until a specified date to boost your maker reputation score, which increases the likelihood of being matched in CoinJoins.

| Option | Description |
|--------|-------------|
| **LIST** | View all existing fidelity bonds and their lock dates |
| **CREATE** | Generate a new bond address and lock coins until a future date |
| **BACK** | Return to the Maker Menu |

---
