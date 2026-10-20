//! Typed, hashable IDs. All IDs are dense u32 indices into `SemanticIndex`
//! arenas; serialization round-trips them as plain integers.

macro_rules! define_id {
    ($(#[$meta:meta])* $name:ident) => {
        $(#[$meta])*
        #[derive(
            Debug, Clone, Copy, Default, PartialEq, Eq, PartialOrd, Ord, Hash,
            serde::Serialize, serde::Deserialize,
        )]
        #[serde(transparent)]
        pub struct $name(pub u32);

        impl $name {
            pub const fn from_raw(v: u32) -> Self {
                Self(v)
            }
            pub const fn raw(self) -> u32 {
                self.0
            }
        }

        impl From<u32> for $name {
            fn from(v: u32) -> Self {
                Self(v)
            }
        }

        impl std::fmt::Display for $name {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                write!(f, "{}#{}", stringify!($name), self.0)
            }
        }
    };
}

define_id!(
    /// A analyzed project/repository.
    ProjectId
);
define_id!(
    /// A runtime service within a project. Runtime identity is tracked by
    /// *module*, not by single classpath: common modules (e.g. `ts-common`)
    /// can run across multiple services.
    ServiceId
);
define_id!(
    /// A source directory/build module.
    ModuleId
);
define_id!(
    /// A source file.
    FileId
);
define_id!(
    /// A named declaration (class, function, field, ..).
    SymbolId
);
define_id!(
    /// A function or method body.
    FunctionId
);
define_id!(
    /// A call site occurrences within a function body.
    CallSiteId
);
define_id!(
    /// A framework-exposed endpoint (route, handler).
    EndpointId
);
define_id!(
    /// A data resource (table, collection, queue, ..).
    ResourceId
);
define_id!(
    /// A guard (branch condition) occurrence.
    GuardId
);
define_id!(
    /// A block of the minimal CFG.
    BlockId
);
