public import Core
public func label(_ state: SendState) -> String {
    switch state {
    case .draft: "Draft"
    case .queued: "Queued"
    case .sent: "Sent"
    case .failed: "Failed"
    }
}
