import SettingsInterface
import UIKit

final class LegacyLabel: UILabel {
    func configure() {
        accessibilityIdentifier = "legacy.label"
    }
}
