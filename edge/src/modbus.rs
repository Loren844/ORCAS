//! Client Modbus TCP du bassin : une connexion, rouverte après toute erreur de transport.

use std::io;
use std::time::Duration;

use thiserror::Error;
use tokio::net::lookup_host;
use tokio::time::timeout;
use tokio_modbus::client::{Context, Reader, tcp};
use tokio_modbus::{ExceptionCode, Slave};

#[derive(Debug, Error)]
pub enum ReadError {
    #[error("connexion à {0} impossible : {1}")]
    Connect(String, #[source] io::Error),
    #[error("pas de réponse sous {0:?}")]
    Timeout(Duration),
    #[error("erreur de transport Modbus : {0}")]
    Transport(#[from] tokio_modbus::Error),
    #[error("exception Modbus : {0}")]
    Exception(ExceptionCode),
    #[error("réponse vide")]
    EmptyResponse,
}

pub struct ModbusClient {
    host: String,
    port: u16,
    unit: Slave,
    timeout: Duration,
    ctx: Option<Context>,
}

impl ModbusClient {
    pub fn new(host: String, port: u16, unit_id: u8, timeout: Duration) -> Self {
        Self {
            host,
            port,
            unit: Slave(unit_id),
            timeout,
            ctx: None,
        }
    }

    /// Lit un *input register*. Toute erreur autre qu'une exception Modbus ferme la connexion,
    /// rouverte à la lecture suivante.
    pub async fn read_input_register(&mut self, address: u16) -> Result<u16, ReadError> {
        let result = self.try_read(address).await;
        if matches!(
            result,
            Err(ReadError::Connect(..) | ReadError::Timeout(_) | ReadError::Transport(_))
        ) {
            self.ctx = None;
        }
        result
    }

    async fn try_read(&mut self, address: u16) -> Result<u16, ReadError> {
        let ctx = match &mut self.ctx {
            Some(ctx) => ctx,
            None => {
                let ctx = self.connect().await?;
                self.ctx.insert(ctx)
            }
        };
        let words = timeout(self.timeout, ctx.read_input_registers(address, 1))
            .await
            .map_err(|_| ReadError::Timeout(self.timeout))??
            .map_err(ReadError::Exception)?;
        words.first().copied().ok_or(ReadError::EmptyResponse)
    }

    async fn connect(&self) -> Result<Context, ReadError> {
        let target = format!("{}:{}", self.host, self.port);
        let connect = async {
            let addr = lookup_host(&target).await?.next().ok_or_else(|| {
                io::Error::new(io::ErrorKind::NotFound, "aucune adresse pour cet hôte")
            })?;
            tcp::connect_slave(addr, self.unit).await
        };
        let ctx = timeout(self.timeout, connect)
            .await
            .map_err(|_| ReadError::Timeout(self.timeout))?
            .map_err(|e| ReadError::Connect(target.clone(), e))?;
        tracing::info!(%target, unit = self.unit.0, "connecté au serveur Modbus");
        Ok(ctx)
    }
}
