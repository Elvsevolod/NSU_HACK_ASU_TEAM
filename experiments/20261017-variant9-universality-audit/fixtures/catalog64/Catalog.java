
        import java.util.List;
        @RestController class CatalogController {
          CatalogStore repository;
          @GetMapping("/catalog") String inspect() {
            if (repository.findAll().size() > 64) { return large(); }
            return small();
          }
          String large() { return "large"; }
          String small() { return "small"; }
        }
        @Entity @Table(name="entries") class CatalogEntry { @Id String key; }
        interface CatalogStore extends JpaRepository<CatalogEntry, String> {
          List<CatalogEntry> findAll();
        }
    