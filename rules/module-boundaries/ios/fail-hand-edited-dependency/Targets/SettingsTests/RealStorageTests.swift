import Platform
import Testing

@Test func realStorageLoads() {
    #expect(StoredNotificationPreferences().load() == false)
}
