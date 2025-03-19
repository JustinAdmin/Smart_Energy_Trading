// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EnergyTrading {
    struct Trade {
        address seller;
        address buyer;
        uint256 energyAmount; // kWh
        uint256 price;        // Price in Wei
        bool completed;
    }

    Trade[] public trades;

    event TradeCreated(uint256 tradeId, address indexed seller, uint256 energyAmount, uint256 price);
    event TradeCompleted(uint256 tradeId, address indexed buyer);

    // Constructor with a pre-populated trade
    constructor() {
        require(address(this) != address(0), "Invalid contract address"); // Ensures the contract itself is valid

        trades.push(Trade({
            seller: msg.sender,
            buyer: address(0),
            energyAmount: 100,
            price: 5 * 10**17, // 0.5 ETH in Wei (500000000000000000)
            completed: false
        }));

        emit TradeCreated(0, msg.sender, 100, 5 * 10**17);
    }

    function createTrade(uint256 energyAmount, uint256 price) public {
        require(energyAmount > 0, "Energy amount must be greater than zero");
        require(price > 0, "Price must be greater than zero");

        trades.push(Trade(msg.sender, address(0), energyAmount, price, false));
        emit TradeCreated(trades.length - 1, msg.sender, energyAmount, price);
    }

    function acceptTrade(uint256 tradeId) public payable {
        require(tradeId < trades.length, "Trade does not exist");

        Trade storage trade = trades[tradeId];
        require(!trade.completed, "Trade already completed");
        require(msg.value == trade.price, "Incorrect price");

        trade.buyer = msg.sender;
        trade.completed = true;

        payable(trade.seller).transfer(msg.value);

        emit TradeCompleted(tradeId, msg.sender);
    }

    function getTrade(uint256 tradeId) public view returns (Trade memory) {
        require(tradeId < trades.length, "Trade does not exist");
        return trades[tradeId];
    }

    function getTradesLength() public view returns (uint256) {
        return trades.length;
    }
}
