import Foundation
import SwiftUI

struct Greeting: View {
    var body: some View { Text(UserDefaults.standard.string(forKey: "name") ?? "") }
}
