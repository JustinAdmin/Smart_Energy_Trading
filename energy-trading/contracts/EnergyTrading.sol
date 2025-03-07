// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract EnergyTrading {
    struct Trade {
        address seller;
        address buyer;
        uint256 energyAmount; // kWh
        uint256 price; // Price in CAD
        bool completed;
    }

    Trade[] public trades;

    event TradeCreated(uint256 tradeId, address seller, uint256 energyAmount, uint256 price);
    event TradeCompleted(uint256 tradeId, address buyer);

    function createTrade(uint256 energyAmount, uint256 price) public {
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
