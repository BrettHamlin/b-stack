import SettingsInterface
import UIKit

final class LegacyLabel: UILabel {
    func configure() {
        self.accessibilityIdentifier = "legacy.label"
    }
}
