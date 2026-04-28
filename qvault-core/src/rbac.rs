use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum Role {
    #[serde(rename = "admin")]
    Admin,
    #[serde(rename = "user")]
    User,
    #[serde(rename = "guest")]
    Guest,
}

impl Role {
    pub fn can_create_user(&self) -> bool {
        matches!(self, Role::Admin)
    }

    pub fn can_store_secret(&self) -> bool {
        matches!(self, Role::Admin | Role::User)
    }

    pub fn can_get_secret(&self) -> bool {
        matches!(self, Role::Admin | Role::User)
    }

    pub fn can_list_users(&self) -> bool {
        matches!(self, Role::Admin)
    }
}
