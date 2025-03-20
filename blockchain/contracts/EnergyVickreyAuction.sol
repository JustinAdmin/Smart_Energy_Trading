// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

contract EnergyVickreyAuction {
    struct Bid {
        bytes32 sealedBid;
        uint deposit;
    }

    address public seller;
    uint public biddingEnd;
    uint public revealEnd;
    bool public ended;
    
    mapping(address => Bid) public bids;
    address[] public bidders;
    
    address public highestBidder;
    uint public highestBid;
    uint public secondHighestBid;
    
    event AuctionEnded(address winner, uint amount);
    
    modifier onlyBefore(uint _time) {
        require(block.timestamp < _time, "Too late");
        _;
    }
    
    modifier onlyAfter(uint _time) {
        require(block.timestamp > _time, "Too early");
        _;
    }
    
    constructor(uint _biddingTime, uint _revealTime) {
        seller = msg.sender;
        biddingEnd = block.timestamp + _biddingTime;
        revealEnd = biddingEnd + _revealTime;
    }
    
    function bid(bytes32 _sealedBid) external payable onlyBefore(biddingEnd) {
        require(bids[msg.sender].sealedBid == 0, "Already bid");
        bids[msg.sender] = Bid({
            sealedBid: _sealedBid,
            deposit: msg.value
        });
        bidders.push(msg.sender);
    }
    
    function reveal(uint _value, bytes32 _nonce) external onlyAfter(biddingEnd) onlyBefore(revealEnd) {
        Bid storage bidToCheck = bids[msg.sender];
        require(bidToCheck.sealedBid != 0, "No bid found");
        require(bidToCheck.sealedBid == keccak256(abi.encodePacked(_value, _nonce)), "Invalid bid reveal");
        require(bidToCheck.deposit >= _value, "Deposit too low");
        
        if (_value > highestBid) {
            secondHighestBid = highestBid;
            highestBid = _value;
            highestBidder = msg.sender;
        } else if (_value > secondHighestBid) {
            secondHighestBid = _value;
        }
    }
    
    function finalizeAuction() external onlyAfter(revealEnd) {
        require(!ended, "Auction already ended");
        ended = true;
        
        if (highestBidder != address(0)) {
            payable(seller).transfer(secondHighestBid);
            payable(highestBidder).transfer(bids[highestBidder].deposit - secondHighestBid);
        }
        
        emit AuctionEnded(highestBidder, secondHighestBid);
    }
}