//! Framework-contract knowledge, kept in one data-driven place.
//!
//! Every entry here is a *public* framework contract (Servlet, Spring Data,
//! Spring Security, JPA). Nothing in this module mentions Train Ticket, a
//! service name, an entity name or a scenario. If a project uses a different
//! stack, the adapter replaces this table; the resolution engine in
//! [`crate::graph`] only consumes its predicates.

/// Spring Data repository base types. A project type extending one of these is
/// backed by a container-generated proxy: its methods have no body in the
/// project, so they never appear in `executes`/`calls`, and the SQL they issue
/// is attributed to the calling method (contest `data` semantics).
pub const REPOSITORY_BASES: &[&str] = &[
    "Repository",
    "CrudRepository",
    "PagingAndSortingRepository",
    "JpaRepository",
    "MongoRepository",
    "JpaSpecificationExecutor",
];

/// Servlet filter contracts: implementations are invoked by the container for
/// every request, without a project-level call site pointing at them.
pub const FILTER_BASES: &[&str] = &["Filter", "OncePerRequestFilter", "HandlerInterceptor"];

/// Spring Security `UserDetailsService`: invoked by the authentication
/// machinery when credentials are checked.
pub const USER_DETAILS_SERVICE: &str = "UserDetailsService";

/// Spring Security `UserDetails`: the authentication machinery reads exactly
/// these members off the principal returned by `loadUserByUsername`.
pub const USER_DETAILS_MEMBERS: &[&str] = &[
    "getAuthorities",
    "getPassword",
    "getUsername",
    "isAccountNonExpired",
    "isAccountNonLocked",
    "isCredentialsNonExpired",
    "isEnabled",
];

/// Strip a generic argument list and a package prefix from a type name:
/// `CrudRepository<User, String>` → `CrudRepository`, `a.b.C` → `C`.
#[must_use]
pub fn simple_name(raw: &str) -> &str {
    let base = raw.split('<').next().unwrap_or(raw).trim();
    let base = base.rsplit('.').next().unwrap_or(base);
    base.rsplit('$').next().unwrap_or(base)
}

/// Whether any declared supertype name matches one of `bases`.
#[must_use]
pub fn has_base(declared: impl Iterator<Item = String>, bases: &[&str]) -> bool {
    declared.filter(|d| bases.contains(&simple_name(d))).count() > 0
}

/// The element type of a container-like return type: `ArrayList<Order>` →
/// `Order`, `Optional<User>` → `User`, `Order` → `Order`, `List<T>` → `T`.
///
/// Only the first *top-level* generic argument is returned, so nested generics
/// survive intact (`List<Map<String, Order>>` → `Map<String, Order>`).
#[must_use]
pub fn element_type(raw: &str) -> Option<String> {
    let raw = raw.trim();
    let Some((_, rest)) = raw.split_once('<') else {
        // A raw array is not an entity container.
        if raw.ends_with("[]") || raw.is_empty() {
            return None;
        }
        return Some(raw.to_owned());
    };
    let (inside, _) = rest.rsplit_once('>')?;
    first_type_argument(inside.trim()).map(str::to_owned)
}

/// First top-level comma-separated argument of a generic argument list.
fn first_type_argument(inside: &str) -> Option<&str> {
    if inside.is_empty() {
        return None;
    }
    let mut depth = 0i32;
    for (i, c) in inside.char_indices() {
        match c {
            '<' => depth += 1,
            '>' => depth -= 1,
            ',' if depth == 0 => return Some(inside[..i].trim()),
            _ => {}
        }
    }
    Some(inside.trim())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn simple_names_strip_generics_and_packages() {
        assert_eq!(simple_name("CrudRepository<User, String>"), "CrudRepository");
        assert_eq!(simple_name("edu.fudan.common.entity.User"), "User");
        assert_eq!(simple_name("SecurityConfig$1"), "1");
        assert_eq!(simple_name("OncePerRequestFilter"), "OncePerRequestFilter");
    }

    #[test]
    fn repository_detection_is_by_contract_name() {
        let declared = vec!["CrudRepository<User, String>".to_owned()];
        assert!(has_base(declared.into_iter(), REPOSITORY_BASES));
        let not_repo = vec!["UserService".to_owned()];
        assert!(!has_base(not_repo.into_iter(), REPOSITORY_BASES));
    }

    #[test]
    fn element_type_unwraps_containers() {
        assert_eq!(element_type("ArrayList<Order>").as_deref(), Some("Order"));
        assert_eq!(element_type("Optional<User>").as_deref(), Some("User"));
        assert_eq!(element_type("Order").as_deref(), Some("Order"));
        assert_eq!(element_type("java.util.List<Map<String, Order>>").as_deref(), Some("Map<String, Order>"));
        assert_eq!(element_type("String[]"), None);
    }

    #[test]
    fn filters_detected_from_raw_supertypes() {
        assert!(has_base(
            vec!["OncePerRequestFilter".to_owned()].into_iter(),
            FILTER_BASES
        ));
    }
}
