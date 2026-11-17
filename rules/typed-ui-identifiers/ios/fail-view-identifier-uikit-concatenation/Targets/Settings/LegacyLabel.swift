import SettingsInterface
import UIKit

final class LegacyLabel: UILabel {
    func configure() {
        accessibilityIdentifier = NotificationSettingsUIID.toggle.rawValue + ".typo"
    }
}
