//! *Anti-Corruption Layer* : traduit les valeurs brutes des capteurs (encodage constructeur,
//! carte Modbus v1) en grandeurs du domaine. Rien en aval ne voit d'unité brute ni de sentinelle.

/// Valeur renvoyée par un capteur en défaut.
pub const SENTINEL: u16 = 0xFFFF;

/// Conversion d'un *input register* brut vers l'unité du domaine.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Conversion {
    /// `raw / diviseur` (ex. 0,01 °C → °C : diviseur 100).
    Scale(f64),
    /// Dixièmes de degré Fahrenheit vers °C : `(raw / 10 − 32) × 5/9`.
    #[allow(dead_code, reason = "utilisée par S02, pas encore interrogé")]
    DeciFahrenheitToCelsius,
}

impl Conversion {
    fn apply(self, raw: u16) -> f64 {
        let raw = f64::from(raw);
        match self {
            Conversion::Scale(divisor) => raw / divisor,
            Conversion::DeciFahrenheitToCelsius => (raw / 10.0 - 32.0) * 5.0 / 9.0,
        }
    }
}

/// Description d'un capteur dans la carte Modbus.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Sensor {
    /// Identifiant métier (`S01`…).
    pub id: &'static str,
    /// Grandeur publiée, dernier segment du topic de mesure.
    pub quantity: &'static str,
    /// Adresse de l'*input register*.
    pub address: u16,
    /// Unité du domaine, après conversion.
    pub unit: &'static str,
    pub conversion: Conversion,
}

impl Sensor {
    /// Valeur dans l'unité du domaine, ou `None` si le capteur signale un défaut.
    pub fn convert(&self, raw: u16) -> Option<f64> {
        (raw != SENTINEL).then(|| self.conversion.apply(raw))
    }
}

/// S01, température de l'eau n°1, en 0,01 °C.
pub const S01: Sensor = Sensor {
    id: "S01",
    quantity: "temperature",
    address: 0,
    unit: "°C",
    conversion: Conversion::Scale(100.0),
};

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_close(actual: Option<f64>, expected: f64) {
        let actual = actual.expect("valeur attendue");
        assert!((actual - expected).abs() < 1e-9, "{actual} ≠ {expected}");
    }

    #[test]
    fn s01_suit_la_carte_modbus() {
        assert_eq!(S01.address, 0);
        assert_eq!(S01.unit, "°C");
        assert_eq!(S01.quantity, "temperature");
    }

    #[test]
    fn s01_centiemes_de_degre_vers_celsius() {
        assert_close(S01.convert(2412), 24.12);
        assert_close(S01.convert(0), 0.0);
        assert_close(S01.convert(1), 0.01);
        assert_close(S01.convert(0xFFFE), 655.34);
    }

    #[test]
    fn sentinelle_donne_une_absence_de_valeur() {
        assert_eq!(S01.convert(SENTINEL), None);
    }

    #[test]
    fn dixiemes_de_fahrenheit_vers_celsius() {
        let sonde_f = Sensor {
            conversion: Conversion::DeciFahrenheitToCelsius,
            ..S01
        };
        assert_close(sonde_f.convert(320), 0.0);
        assert_close(sonde_f.convert(2120), 100.0);
        assert_close(sonde_f.convert(770), 25.0);
        assert_close(sonde_f.convert(0), -160.0 / 9.0);
        assert_eq!(sonde_f.convert(SENTINEL), None);
    }

    #[test]
    fn autres_echelles() {
        let scale = |divisor| Sensor {
            conversion: Conversion::Scale(divisor),
            ..S01
        };
        assert_close(scale(10.0).convert(355), 35.5);
        assert_close(scale(1000.0).convert(42), 0.042);
        assert_close(scale(1.0).convert(1500), 1500.0);
    }
}
