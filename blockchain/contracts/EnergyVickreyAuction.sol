// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

contract EnergyVickreyAuction {
    struct Bid {
        bytes32 sealedBid;
        uint256 deposit;
    }

    address public seller;
    uint256 public biddingEnd;
    uint256 public revealEnd;
    bool public ended;

    mapping(address => Bid) public bids;
    address[] public bidders;

    address public highestBidder;
    uint256 public highestBid;
    uint256 public secondHighestBid;

    event BidPlaced(address indexed bidder, uint256 deposit);
    event BidRevealed(address indexed bidder, uint256 value);
    event AuctionEnded(address winner, uint256 winningBid);

    modifier onlyBefore(uint256 _time) {
        require(block.timestamp < _time, "Too late");
        _;
    }

    modifier onlyAfter(uint256 _time) {
        require(block.timestamp > _time, "Too early");
        _;
    }

    modifier auctionNotEnded() {
        require(!ended, "Auction already ended");
        _;
    }

    constructor(uint256 _biddingTime, uint256 _revealTime) {
        seller = msg.sender;
        biddingEnd = block.timestamp + _biddingTime;
        revealEnd = biddingEnd + _revealTime;
    }

    // Submit a sealed bid
    function bid(bytes32 _sealedBid) external payable onlyBefore(biddingEnd) {
        require(bids[msg.sender].sealedBid == bytes32(0), "Already bid");
        require(msg.value > 0, "Deposit must be greater than 0");

        bids[msg.sender] = Bid({
            sealedBid: _sealedBid,
            deposit: msg.value
        });
        bidders.push(msg.sender);

        emit BidPlaced(msg.sender, msg.value);
    }

    // Reveal the actual bid during the reveal phase
    function reveal(uint256 _value, bytes32 _nonce)
        external
        onlyAfter(biddingEnd)
        onlyBefore(revealEnd)
    {
        Bid storage bidToCheck = bids[msg.sender];
        require(bidToCheck.sealedBid != bytes32(0), "No bid found");
        require(
            bidToCheck.sealedBid == keccak256(abi.encodePacked(_value, _nonce)),
            "Invalid bid reveal"
        );
        require(bidToCheck.deposit >= _value, "Deposit too low");

        if (_value > highestBid) {
            secondHighestBid = highestBid;
            highestBid = _value;
            highestBidder = msg.sender;
        } else if (_value > secondHighestBid) {
            secondHighestBid = _value;
        }

        emit BidRevealed(msg.sender, _value);
    }

    // Finalize the auction and distribute funds
    function finalizeAuction() external onlyAfter(revealEnd) auctionNotEnded {
        ended = true;

        if (highestBidder != address(0)) {
            // Transfer the second highest bid amount to the seller
            payable(seller).transfer(secondHighestBid);

            // Refund the highest bidder's deposit minus the second highest bid
            payable(highestBidder).transfer(
                bids[highestBidder].deposit - secondHighestBid
            );
        }

        // Refund all non-winning bidders
        for (uint256 i = 0; i < bidders.length; i++) {
            address bidder = bidders[i];
            if (bidder != highestBidder) {
                uint256 refundAmount = bids[bidder].deposit;
                bids[bidder].deposit = 0; // Prevent re-entrancy
                if (refundAmount > 0) {
                    payable(bidder).transfer(refundAmount);
                }
            }
        }

        emit AuctionEnded(highestBidder, secondHighestBid);
    }
}
