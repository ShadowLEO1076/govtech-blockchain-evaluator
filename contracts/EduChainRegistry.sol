// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title EduChain Registry
 * @notice Registro inmutable de evaluaciones docentes en blockchain.
 *         Desplegado en Syscoin Tanenbaum Testnet (Chain ID: 5700).
 * @dev    Parte del proyecto EduChain GovTech Auditor — ODS 4 & 16.
 *         Solo el owner (wallet del bot auditor) puede registrar evaluaciones.
 *         Cualquiera puede verificar hashes y consultar evaluaciones.
 */
contract EduChainRegistry {

    // ─────────────────────────────────────────────
    //  Estado
    // ─────────────────────────────────────────────

    address public owner;
    uint256 public totalEvaluaciones;

    struct Evaluacion {
        string  docenteId;      // Identificador del docente (ej: "DOC-123" o nombre)
        bytes32 dataHash;       // SHA-256 del JSON completo de evaluación
        uint16  scoreFinal;     // score * 100 para evitar decimales (ej: 3.25 → 325)
        uint40  timestamp;      // block.timestamp al momento del registro
        bool    alerta;         // true si score < 2.0 (requiere plan de mejora)
    }

    /// @notice Mapping de bloque# (1-indexed) → Evaluacion
    mapping(uint256 => Evaluacion) public evaluaciones;

    /// @notice Verifica si un hash ya fue registrado (anti-duplicados)
    mapping(bytes32 => bool) public hashRegistrado;

    // ─────────────────────────────────────────────
    //  Eventos
    // ─────────────────────────────────────────────

    event EvaluacionRegistrada(
        uint256 indexed bloque,
        string  docenteId,
        bytes32 dataHash,
        uint16  scoreFinal,
        bool    alerta,
        uint40  timestamp
    );

    event OwnerTransferido(address indexed anterior, address indexed nuevo);

    // ─────────────────────────────────────────────
    //  Modificadores
    // ─────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "EduChain: Solo el auditor autorizado");
        _;
    }

    // ─────────────────────────────────────────────
    //  Constructor
    // ─────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ─────────────────────────────────────────────
    //  Funciones de Escritura
    // ─────────────────────────────────────────────

    /**
     * @notice Registra una evaluación docente de forma inmutable.
     * @param _docenteId  Identificador o nombre del docente
     * @param _dataHash   Hash SHA-256 del JSON de evaluación (como bytes32)
     * @param _scoreFinal Score final multiplicado por 100 (ej: 325 = 3.25)
     * @param _alerta     true si el docente requiere plan de mejora
     */
    function registrarEvaluacion(
        string calldata _docenteId,
        bytes32 _dataHash,
        uint16  _scoreFinal,
        bool    _alerta
    ) external onlyOwner {
        require(!hashRegistrado[_dataHash], "EduChain: Evaluacion ya registrada");
        require(bytes(_docenteId).length > 0, "EduChain: docenteId vacio");

        totalEvaluaciones++;

        evaluaciones[totalEvaluaciones] = Evaluacion({
            docenteId:  _docenteId,
            dataHash:   _dataHash,
            scoreFinal: _scoreFinal,
            timestamp:  uint40(block.timestamp),
            alerta:     _alerta
        });

        hashRegistrado[_dataHash] = true;

        emit EvaluacionRegistrada(
            totalEvaluaciones,
            _docenteId,
            _dataHash,
            _scoreFinal,
            _alerta,
            uint40(block.timestamp)
        );
    }

    /**
     * @notice Transfiere la propiedad del contrato a otra wallet.
     * @param _nuevoOwner Dirección del nuevo owner
     */
    function transferirOwner(address _nuevoOwner) external onlyOwner {
        require(_nuevoOwner != address(0), "EduChain: Direccion invalida");
        emit OwnerTransferido(owner, _nuevoOwner);
        owner = _nuevoOwner;
    }

    // ─────────────────────────────────────────────
    //  Funciones de Lectura
    // ─────────────────────────────────────────────

    /**
     * @notice Verifica si un hash específico ya fue registrado.
     * @param _hash El hash a verificar
     * @return true si el hash existe en el registro
     */
    function verificarHash(bytes32 _hash) external view returns (bool) {
        return hashRegistrado[_hash];
    }

    /**
     * @notice Obtiene los datos de una evaluación por su número de bloque.
     * @param _bloque Número de bloque (1-indexed)
     */
    function obtenerEvaluacion(uint256 _bloque) external view returns (
        string memory docenteId,
        bytes32 dataHash,
        uint16  scoreFinal,
        uint40  timestamp,
        bool    alerta
    ) {
        require(_bloque > 0 && _bloque <= totalEvaluaciones, "EduChain: Bloque inexistente");
        Evaluacion storage e = evaluaciones[_bloque];
        return (e.docenteId, e.dataHash, e.scoreFinal, e.timestamp, e.alerta);
    }
}
